from __future__ import annotations

import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from ..agent.approval import approval_diff, approval_summary
from ..agent.orchestrator import run_agent_task
from ..ask.orchestrator import answer_question
from ..plan.orchestrator import execute_plan_steps
from ..plan.planner import generate_plan
from .auth import is_owner
from .sessions import ApprovalSession, PlanSession, approval_sessions, plan_sessions


WELCOME = "\n".join(
    [
        "Hi, I am Scraplet.",
        "/ask <question> - ask about the codebase",
        "/agent <goal> - let the agent stage code changes",
        "/plan <goal> - generate and execute a plan",
    ]
)


def _clip(text: str, limit: int = 3900) -> str:
    return text if len(text) <= limit else text[:limit] + "\n...[truncated]"


def _arg(text: str, name: str) -> str:
    return text.replace(f"/{name}", "", 1).strip()


async def _reject_if_not_owner(update: Update) -> bool:
    chat = update.effective_chat
    return not chat or not is_owner(chat.id)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _reject_if_not_owner(update):
        return
    await update.message.reply_text(WELCOME)


async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _reject_if_not_owner(update):
        return
    question = _arg(update.message.text or "", "ask")
    if not question:
        await update.message.reply_text("Usage: /ask <question>")
        return
    await update.message.reply_text("Researching...")
    result = await asyncio.to_thread(answer_question, question)
    await update.message.reply_text(_clip(result.answer))


async def agent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _reject_if_not_owner(update):
        return
    goal = _arg(update.message.text or "", "agent")
    if not goal:
        await update.message.reply_text("Usage: /agent <goal>")
        return
    await update.message.reply_text("Agent is working...")
    result = await asyncio.to_thread(run_agent_task, goal)
    if result.text.strip():
        await update.message.reply_text(_clip(result.text))
    await _finish_or_approve(update.effective_chat.id, update, result.tracker, result.executor)


async def plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _reject_if_not_owner(update):
        return
    goal = _arg(update.message.text or "", "plan")
    if not goal:
        await update.message.reply_text("Usage: /plan <goal>")
        return
    await update.message.reply_text("Generating plan...")
    draft = await asyncio.to_thread(generate_plan, goal)
    chat_id = update.effective_chat.id
    plan_sessions[chat_id] = PlanSession(
        plan=draft,
        selected={step.id for step in draft.steps},
    )
    await update.message.reply_text(
        _plan_message(plan_sessions[chat_id]),
        reply_markup=_plan_keyboard(plan_sessions[chat_id]),
    )


def _plan_message(session: PlanSession) -> str:
    lines = [f"Plan for: {session.plan.goal}", ""]
    for index, step in enumerate(session.plan.steps, start=1):
        mark = "[x]" if step.id in session.selected else "[ ]"
        tag = f" [{step.complexity}]" if step.complexity else ""
        lines.append(f"{mark} {index}. {step.title}{tag}")
    lines.append("")
    lines.append("Tap steps to toggle, then Proceed.")
    return "\n".join(lines)


def _plan_keyboard(session: PlanSession) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                f"{'[x]' if step.id in session.selected else '[ ]'} Step {index}",
                callback_data=f"plan_toggle:{step.id}",
            )
        ]
        for index, step in enumerate(session.plan.steps, start=1)
    ]
    rows.extend(
        [
            [
                InlineKeyboardButton("Select all", callback_data="plan_all"),
                InlineKeyboardButton("Deselect all", callback_data="plan_none"),
            ],
            [InlineKeyboardButton("Proceed", callback_data="plan_proceed")],
        ]
    )
    return InlineKeyboardMarkup(rows)


async def plan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or await _reject_if_not_owner(update):
        return
    chat_id = query.message.chat_id
    session = plan_sessions.get(chat_id)
    if not session:
        await query.answer()
        return

    data = query.data or ""
    if data.startswith("plan_toggle:"):
        step_id = data.split(":", 1)[1]
        if step_id in session.selected:
            session.selected.remove(step_id)
        else:
            session.selected.add(step_id)
        await query.edit_message_text(
            _plan_message(session),
            reply_markup=_plan_keyboard(session),
        )
        await query.answer()
        return

    if data == "plan_all":
        session.selected = {step.id for step in session.plan.steps}
        await query.edit_message_text(
            _plan_message(session),
            reply_markup=_plan_keyboard(session),
        )
        await query.answer()
        return

    if data == "plan_none":
        session.selected.clear()
        await query.edit_message_text(
            _plan_message(session),
            reply_markup=_plan_keyboard(session),
        )
        await query.answer()
        return

    if data == "plan_proceed":
        steps = [step for step in session.plan.steps if step.id in session.selected]
        plan_sessions.pop(chat_id, None)
        if not steps:
            await query.answer("No steps selected")
            return
        await query.edit_message_text(f"Executing {len(steps)} step(s)...")
        result = await asyncio.to_thread(execute_plan_steps, session.plan, steps)
        for output in result.outputs:
            if output.strip():
                await query.message.reply_text(_clip(output))
        await _finish_or_approve(chat_id, update, result.tracker, result.executor)
        await query.answer()


async def approval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or await _reject_if_not_owner(update):
        return
    chat_id = query.message.chat_id
    session = approval_sessions.get(chat_id)
    if not session:
        await query.answer()
        return

    if query.data == "approval_diff":
        await query.message.reply_text(_clip(approval_diff(session.pending)))
        await query.answer()
        return

    if query.data == "approval_accept":
        approval_sessions.pop(chat_id, None)
        for action in session.pending:
            session.tracker.update_status(action.id, "approved", True)
        errors = await asyncio.to_thread(session.executor.apply_approved_from_tracker)
        session.executor.clear_staging()
        message = "All changes applied." if not errors else "Applied with errors:\n" + "\n".join(errors)
        await query.edit_message_text(_clip(message))
        await query.answer("Applied")
        return

    if query.data == "approval_reject":
        approval_sessions.pop(chat_id, None)
        for action in session.pending:
            session.tracker.update_status(action.id, "rejected", False)
        session.executor.clear_staging()
        await query.edit_message_text("All changes rejected. Nothing was applied.")
        await query.answer("Rejected")


async def _finish_or_approve(
    chat_id: int,
    update: Update,
    tracker,
    executor,
) -> None:
    pending = tracker.get_pending_mutations()
    if not pending:
        await update.effective_chat.send_message("Done. No file changes were needed.")
        return

    approval_sessions[chat_id] = ApprovalSession(
        tracker=tracker,
        executor=executor,
        pending=pending,
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Show diff", callback_data="approval_diff")],
            [
                InlineKeyboardButton("Accept all", callback_data="approval_accept"),
                InlineKeyboardButton("Reject all", callback_data="approval_reject"),
            ],
        ]
    )
    await update.effective_chat.send_message(
        approval_summary(pending),
        reply_markup=keyboard,
    )


def register_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ask", ask))
    application.add_handler(CommandHandler("agent", agent))
    application.add_handler(CommandHandler("plan", plan))
    application.add_handler(CallbackQueryHandler(plan_callback, pattern=r"^plan_"))
    application.add_handler(CallbackQueryHandler(approval_callback, pattern=r"^approval_"))
