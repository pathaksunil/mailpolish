# from app.models.rewrite import RewriteMode
import logging

logger = logging.getLogger("app.providers.prompts")

MODE_INSTRUCTIONS = {
    # ============================================================
    # EMAIL
    # ============================================================

    "✉️ Professional Reply":
        "Rewrite the text as a polished, professional, and courteous email reply. "
        "Use clear business language and an appropriate email structure.",

    "⚡ Make Concise & Direct":
        "Make the text shorter, clearer, and more direct. "
        "Remove unnecessary words while preserving the original meaning and important details.",

    "🛡️ Soften & De-escalate":
        "Rewrite the text using calm, diplomatic, and non-confrontational language. "
        "Reduce tension while preserving the intended message, requests, and boundaries.",

    "📅 Meeting Agenda Formatter":
        "Convert the content into a clear and structured meeting agenda. "
        "Identify relevant topics, objectives, discussion points, and action items when present.",

    "💼 Executive Client Polish":
        "Rewrite the text in polished, executive-level business language suitable for an important client. "
        "Make it professional, confident, concise, and client-focused.",

    "🎯 Action-Item Extractor":
        "Extract and organize the actionable tasks, responsibilities, decisions, deadlines, and next steps "
        "contained in the text. Do not invent missing information.",

    "🧹 Zero-Error Grammar Check":
        "Correct grammar, spelling, punctuation, syntax, and awkward phrasing. "
        "Preserve the original meaning, tone, and factual information.",

    "🤝 Follow-up Generator":
        "Transform the content into a professional follow-up message. "
        "Clearly communicate what is being followed up on and the appropriate next step.",

    "🚨 The 'Wake-Up Call' (Blunt Stinker)":
        "Rewrite the message to be blunt, direct, and strongly worded while remaining professional. "
        "Communicate urgency clearly without using insults, threats, or unnecessary hostility.",

    "🛑 Firm Pushback & Boundaries":
        "Rewrite the message with clear, firm boundaries and assertive language. "
        "Be confident and direct while remaining professional and respectful.",

    "🌸 Honey-Coated (Ultra-Polite)":
        "Rewrite the message in an exceptionally polite, warm, tactful, and considerate manner. "
        "Make requests and disagreements sound respectful without changing their meaning.",

    "☕ Casual & Conversational":
        "Rewrite the text in a natural, relaxed, friendly, and conversational style. "
        "Avoid overly formal or corporate language.",

    "🤪 Witty & Lighthearted (Funny)":
        "Rewrite the text with tasteful wit and light humor while preserving the original purpose, "
        "meaning, and important information. Keep the humor appropriate for the context.",

    "🧊 The Corporate Cold-Shoulder":
        "Rewrite the message in a restrained, formal, emotionally neutral corporate style. "
        "Be professional, concise, and detached without being rude.",

    "⏳ Final Notice & Hardline":
        "Rewrite the message as a firm final notice. Clearly communicate urgency, expectations, "
        "deadlines, and consequences when those details are already present in the source text. "
        "Do not invent deadlines or consequences.",

    "🎉 High-Energy Cheerleader":
        "Rewrite the message with an enthusiastic, positive, motivating, and energetic style. "
        "Maintain professionalism and preserve the original meaning.",


    # ============================================================
    # WORD
    # ============================================================

    "📌 Executive Summary":
        "Use document format, not email. No subject, greeting, sign-off, or signature unless requested."
        "Convert the text into a concise executive summary. "
        "Highlight as needed (such as findings, decisions, outcomes, risks, and recommendations..) "
        "when they are present in the source.",

    "✍️ Academic & Professional Rewrite":
        "Use document format, not email. No subject, greeting, sign-off, or signature unless requested."
        "Rewrite the text in a formal, precise, polished academic and professional style. "
        "Improve terminology, clarity, structure, and scholarly readability without inventing information.",

    "✂️ Simplify & Clarify Jargon":
        "Use document format, not email. No subject, greeting, sign-off, or signature unless requested."
        "Simplify complex language, technical terminology, and jargon so the text is easier to understand. "
        "Preserve the original meaning and important technical details.",

    "💡 Expand & Elaborate Context":
        "Use document format, not email. No subject, greeting, sign-off, or signature unless requested."
        "Expand the text with clearer explanations, useful context, and logical detail. "
        "Do not invent facts, evidence, examples, or claims that are not supported by the source.",

    "🔄 Improve Flow & Transitions":
        "Use document format, not email. No subject, greeting, sign-off, or signature unless requested."
        "Improve the logical flow, coherence, sentence structure, and transitions between ideas. "
        "Ensure the text reads naturally and logically while preserving its meaning.",

    "🎯 Argument Strengthener":
        "Use document format, not email. No subject, greeting, sign-off, or signature unless requested."
        "Strengthen the presentation and structure of the argument. "
        "Improve reasoning, clarity, organization, and connections between claims and evidence. "
        "Do not invent evidence or unsupported claims.",

    "📝 Convert to Formal Letter/Memo":
        "Use document format, not email. No subject, greeting, sign-off, or signature unless requested."
        "Convert the content into a properly structured formal letter or professional memo. "
        "Use an appropriate formal structure while preserving the original information.",

    "🧹 Deep Grammar & Syntax Edit":
        "Use document format, not email. No subject, greeting, sign-off, or signature unless requested."
        "Perform a thorough grammar, spelling, punctuation, syntax, sentence-structure, and language edit. "
        "Improve readability while preserving the author's meaning and voice.",


    # ============================================================
    # POWERPOINT
    # ============================================================

    "📊 Corporate / Modern (8-12 slides)":
        "Create a polished, modern, corporate-style PowerPoint presentation from the provided content. "
        "Structure the content into approximately 8-12 slides. "
        "Use clear slide titles, concise bullet points, logical flow, and professional business language. "
        "Prioritize key information, insights, decisions, metrics, and takeaways. "
        "Avoid overcrowding slides.",

    "🗣️ Executive / Streategic (5-8 Slides)":
        "Create an executive-level, strategic PowerPoint presentation from the provided content. "
        "Structure the content into approximately 5-8 slides. "
        "Focus on the most important strategic messages, business implications, decisions, risks, opportunities, "
        "and recommendations. Keep the presentation concise, high-level, and suitable for senior leadership.",

    "⏱️ 30-Second Elevator Pitch (5-6 Slides)":
        "Create a concise and compelling PowerPoint presentation designed to communicate the core message "
        "in approximately 30 seconds. Structure the content into 5-6 slides. "
        "Focus on the problem, key insight or solution, value proposition, and main takeaway. "
        "Keep every slide highly focused and concise.",

    "🎯 Academic / Lecture (15-20 Slides)":
        "Create a structured academic or lecture-style PowerPoint presentation from the provided content. "
        "Structure the content into approximately 15-20 slides. "
        "Provide clear explanations, logical progression of concepts, definitions, examples, evidence, "
        "and key takeaways where supported by the source material. "
        "Maintain a formal and educational tone.",

    "🧩 Sales Pitch  (10-15 SlideS)":
        "Create a persuasive but professional sales-pitch PowerPoint presentation from the provided content. "
        "Structure the content into approximately 10-15 slides. "
        "Highlight the customer problem, relevant solution, key benefits, value proposition, differentiators, "
        "supporting evidence, and call to action when those details are available. "
        "Do not invent product capabilities, statistics, claims, or customer information.",

    "📈 Technical Deep Dive  (15-20 Slides)":
        "Create a detailed technical PowerPoint presentation from the provided content. "
        "Structure the content into approximately 15-20 slides. "
        "Cover technical concepts, architecture, processes, implementation details, data, dependencies, "
        "trade-offs, limitations, and conclusions when supported by the source material. "
        "Use precise technical language while keeping each slide readable.",

    "⚖️ Creative / Visionary (8-12 Slides)":
        "Create a creative, visionary PowerPoint presentation from the provided content. "
        "Structure the content into approximately 8-12 slides. "
        "Build a compelling narrative around the central idea, vision, opportunity, transformation, "
        "and desired outcome. Use concise, engaging slide content while preserving the original meaning "
        "and avoiding unsupported claims.",
        
    # ============================================================
    # BROWSER
    # ============================================================

    "✨ Polish Web Text":
        "Rewrite the text to be polished, clear, readable, and suitable for publication on a website. "
        "Improve readability and web-friendly structure without changing the meaning.",

    "📝 Summarize Article":
        "Summarize the article or selected content by extracting its key points, findings, arguments, "
        "and conclusions. Remove unnecessary detail.",

    "💡 Simplify Explanation":
        "Explain the content using simpler, clearer language. "
        "Reduce complexity and jargon while preserving the important information.",

    "🔄 Professional Rewrite":
        "Rewrite the content in a polished, professional, clear, and well-structured style.",


    # ============================================================
    # DEFAULT
    # ============================================================

    "✨ Polish Text":
        "Polish the text for clarity, readability, grammar, and overall quality "
        "while preserving the original meaning and voice.",

    "🔍 Check Grammar":
        "Correct grammar, spelling, punctuation, syntax, and obvious language errors "
        "without unnecessarily changing the author's wording or meaning.",

    "📝 Summarize Selection":
        "Summarize the selected text and retain only the most important information, "
        "key points, findings, and conclusions.",

    "🔄 Rewrite Better":
        "Rewrite the text to improve clarity, readability, structure, grammar, and overall quality "
        "while preserving its original meaning.",
}


def build_rewrite_prompt(
    mode: str,
    text: str,
    max_words: int = 200,
    instructions: str = "",
    output_format: str = "plain_text",
) -> str:

    mode_instruction = MODE_INSTRUCTIONS.get(mode)
    if not mode_instruction:
        raise ValueError(f"Unknown rewrite mode: {mode}")

    logger.info(f"Mode: {mode}   instructions : {instructions}")
    
    
    prompt = (
        f"{mode_instruction} Aim for around {max_words} words. "
        "Return only the revised text. No preamble, commentary, or closing note."
    )
    if instructions:
        prompt += f" Additional user guidelines: {instructions}"
    if output_format == "markdown":
        prompt += (
            " Output only clean Markdown—no code fences, HTML, or explanatory"
            " preamble. Use headings and subheadings only when they improve"
            " structure, use lists for grouped points or steps, and use bold"
            " sparingly for important labels."
        )
    prompt += f"\n\nEmail text:\n{text}"
    return prompt
