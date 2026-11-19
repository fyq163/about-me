#!/usr/bin/env python3
"""Convert the resume's LaTeX structure into a readable Markdown file."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


COMMAND_RE = re.compile(r"\\([A-Za-z]+)\*?")


def strip_comments(source: str) -> str:
    """Remove LaTeX comments while keeping escaped percent signs."""
    kept_lines = []
    for line in source.splitlines():
        comment_at = None
        for index, char in enumerate(line):
            if char != "%":
                continue
            backslashes = 0
            previous = index - 1
            while previous >= 0 and line[previous] == "\\":
                backslashes += 1
                previous -= 1
            if backslashes % 2 == 0:
                comment_at = index
                break
        kept_lines.append(line if comment_at is None else line[:comment_at])
    return "\n".join(kept_lines)


def read_group(source: str, opening: int) -> tuple[str, int]:
    """Read a balanced {...} group, returning its content and end offset."""
    if opening >= len(source) or source[opening] != "{":
        raise ValueError(f"Expected '{{' at offset {opening}")

    depth = 0
    for index in range(opening, len(source)):
        char = source[index]
        if char in "{}":
            backslashes = 0
            previous = index - 1
            while previous >= 0 and source[previous] == "\\":
                backslashes += 1
                previous -= 1
            if backslashes % 2 == 0:
                depth += 1 if char == "{" else -1
                if depth == 0:
                    return source[opening + 1 : index], index + 1

    raise ValueError(f"Unclosed group at offset {opening}")


def read_arguments(source: str, position: int, count: int) -> tuple[list[str], int]:
    arguments = []
    cursor = position
    for _ in range(count):
        while cursor < len(source) and source[cursor].isspace():
            cursor += 1
        argument, cursor = read_group(source, cursor)
        arguments.append(argument)
    return arguments, cursor


def commands(source: str, name: str, argument_count: int):
    """Yield each command's arguments and the source range it occupies."""
    pattern = re.compile(rf"\\{re.escape(name)}(?![A-Za-z])")
    cursor = 0
    while match := pattern.search(source, cursor):
        try:
            args, end = read_arguments(source, match.end(), argument_count)
        except ValueError:
            cursor = match.end()
            continue
        yield args, match.start(), end
        cursor = end


def convert_inline(source: str) -> str:
    """Convert the inline LaTeX formatting used in this resume."""
    output = []
    cursor = 0
    while cursor < len(source):
        char = source[cursor]
        if char == "\\":
            if source.startswith("\\\\", cursor):
                output.append(" ")
                cursor += 2
                continue

            match = COMMAND_RE.match(source, cursor)
            if match is None:
                if cursor + 1 < len(source):
                    escaped = source[cursor + 1]
                    output.append(
                        {
                            "&": "&",
                            "%": "%",
                            "$": "$",
                            "#": "#",
                            "_": "_",
                            "{": "{",
                            "}": "}",
                            "~": " ",
                        }.get(escaped, escaped)
                    )
                    cursor += 2
                    continue
                output.append(char)
                cursor += 1
                continue

            name = match.group(1)
            cursor = match.end()
            if name in {"textbf", "textit", "underline", "emph"}:
                while cursor < len(source) and source[cursor].isspace():
                    cursor += 1
                content, cursor = read_group(source, cursor)
                rendered = convert_inline(content)
                if name == "textbf":
                    output.append(f"**{rendered}**")
                elif name in {"textit", "emph"}:
                    output.append(f"*{rendered}*")
                else:
                    output.append(rendered)
                continue

            if name == "href":
                while cursor < len(source) and source[cursor].isspace():
                    cursor += 1
                url, cursor = read_group(source, cursor)
                while cursor < len(source) and source[cursor].isspace():
                    cursor += 1
                label, cursor = read_group(source, cursor)
                rendered_label = convert_inline(label)
                rendered_url = convert_inline(url)
                if rendered_url.endswith("/...") and re.match(
                    r"(?:https?://)?(?:www\.)?[\w.-]+/", rendered_label
                ):
                    rendered_url = f"https://{rendered_label.removeprefix('https://')}"
                output.append(f"[{rendered_label}]({rendered_url})")
                continue

            if name == "textcolor":
                color, cursor = read_group(source, cursor)
                while cursor < len(source) and source[cursor].isspace():
                    cursor += 1
                content, cursor = read_group(source, cursor)
                if convert_inline(color).strip().lower() != "white":
                    output.append(convert_inline(content))
                continue

            if name in {"vspace", "hspace", "fontsize", "color"}:
                while cursor < len(source) and source[cursor].isspace():
                    cursor += 1
                if cursor < len(source) and source[cursor] == "*":
                    cursor += 1
                if cursor < len(source) and source[cursor] == "{":
                    _, cursor = read_group(source, cursor)
                if name == "fontsize":
                    while cursor < len(source) and source[cursor].isspace():
                        cursor += 1
                    if cursor < len(source) and source[cursor] == "{":
                        _, cursor = read_group(source, cursor)
                continue

            if name in {
                "Huge",
                "huge",
                "large",
                "small",
                "footnotesize",
                "scriptsize",
                "tiny",
                "scshape",
                "normalfont",
                "raggedright",
            }:
                continue

            # Keep the contents of unknown formatting commands, but omit the command.
            while cursor < len(source) and source[cursor].isspace():
                cursor += 1
            if cursor < len(source) and source[cursor] == "{":
                content, cursor = read_group(source, cursor)
                output.append(convert_inline(content))
            continue

        if char == "{":
            content, cursor = read_group(source, cursor)
            output.append(convert_inline(content))
            continue

        if char == "}":
            cursor += 1
            continue

        output.append(" " if char == "~" else char)
        cursor += 1

    text = "".join(output).replace("---", "—").replace("--", "–")
    return re.sub(r"\s+", " ", text).strip()


def document_body(source: str) -> str:
    source = strip_comments(source)
    start = source.find(r"\begin{document}")
    end = source.find(r"\end{document}", start + 1)
    if start < 0 or end < 0:
        raise ValueError("Input must contain a complete document environment.")
    body = source[start + len(r"\begin{document}") : end]
    return re.sub(
        r"\\begin\{textblock\}.*?\\end\{textblock\}", "", body, flags=re.DOTALL
    )


def extract_sections(body: str) -> list[tuple[str, str]]:
    sections = list(commands(body, "section", 1))
    result = []
    for index, (args, _, end) in enumerate(sections):
        next_start = sections[index + 1][1] if index + 1 < len(sections) else len(body)
        result.append((convert_inline(args[0]), body[end:next_start]))
    return result


def render_header(body: str) -> list[str]:
    match = re.search(r"\\begin\{center\}(.*?)\\end\{center\}", body, re.DOTALL)
    if not match:
        return []

    center = match.group(1)
    name_match = next(commands(center, "textbf", 1), None)
    if name_match is None:
        return []
    name = convert_inline(name_match[0][0])
    contact = center[name_match[2] :]
    contact = re.sub(r"\\vspace\*?\s*\{[^}]*\}", "", contact)
    contact = contact.replace("$|$", "|").replace("$", "")
    contact = convert_inline(contact.replace("|", " · "))
    contact = re.sub(r"(?:\s*·\s*)+$", "", contact)
    contact = re.sub(r"\s*·\s*", " · ", contact).strip(" ·")
    lines = [f"# {name}"]
    if contact:
        lines.extend(["", contact])
    return lines


def render_skills(section: str) -> list[str]:
    lines = []
    cursor = 0
    pattern = re.compile(r"\\textbf(?![A-Za-z])")
    while match := pattern.search(section, cursor):
        try:
            label_args, label_end = read_arguments(section, match.end(), 1)
            value_args, value_end = read_arguments(section, label_end, 1)
        except ValueError:
            cursor = match.end()
            continue
        label = convert_inline(label_args[0])
        value = convert_inline(value_args[0]).lstrip(": ").strip()
        if label and value:
            lines.append(f"- **{label}:** {value}")
        cursor = value_end
    return lines


def render_entries(section: str, section_name: str) -> list[str]:
    subheadings = list(commands(section, "resumeSubheading", 4))
    lines = []
    for index, (fields, _, end) in enumerate(subheadings):
        next_start = (
            subheadings[index + 1][1] if index + 1 < len(subheadings) else len(section)
        )
        first, second, third, fourth = [convert_inline(field) for field in fields]

        if section_name == "Education":
            title = first
            detail = f"{third} · {second} · {fourth}"
        else:
            title = first
            detail = f"{third} · {fourth} · {second}"

        lines.extend([f"### {title}", "", detail])
        entry_body = section[end:next_start]
        for item_args, _, _ in commands(entry_body, "resumeItem", 1):
            item = convert_inline(item_args[0])
            if item:
                lines.append(f"- {item}")
        lines.append("")
    return lines


def convert(source: str) -> str:
    body = document_body(source)
    output = render_header(body)
    output.append("")

    for title, contents in extract_sections(body):
        markdown_title = {"Experiences": "Experience"}.get(title, title)
        output.extend([f"## {markdown_title}", ""])
        if title == "Skills":
            output.extend(render_skills(contents))
            output.append("")
        else:
            output.extend(render_entries(contents, title))

    markdown = "\n".join(output).strip() + "\n"
    return re.sub(r"\n{3,}", "\n\n", markdown)


def main() -> None:
    default_input = Path(__file__).with_name("main.tex")
    default_output = Path(__file__).with_name("main.md")

    parser = argparse.ArgumentParser(
        description="Convert the structured LaTeX resume to Markdown."
    )
    parser.add_argument("input", nargs="?", type=Path, default=default_input)
    parser.add_argument("output", nargs="?", type=Path, default=default_output)
    args = parser.parse_args()

    markdown = convert(args.input.read_text(encoding="utf-8"))
    args.output.write_text(markdown, encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
