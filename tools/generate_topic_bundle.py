#!/usr/bin/env python3
"""Generate a dual-format CSV bundle for any concept or problem.

The bundle includes:
- one horizontal 60-second short
- one vertical 180-second lecture

This keeps the content model consistent with the existing CSV pipeline while
making it easy to create a concept/problem story in either style.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import textwrap
from pathlib import Path


HEADER = [
    "video_id",
    "concept_type",
    "header_title",
    "tagline",
    "question_text",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "correct_answer",
    "equations_json",
    "visual_data_json",
    "audio_script",
    "orientation",
    "beats_json",
    "target_duration_sec",
]


def _slug(value: str) -> str:
    cleaned = ''.join(ch.lower() if ch.isalnum() else '_' for ch in value.strip())
    cleaned = cleaned.strip('_')
    return cleaned or 'topic'


def _visuals(orientation: str, concept: str, problem: str,
             archetype: str = "concept_map",
             energy_change: float | None = None) -> list[dict]:
    if archetype == "falling_energy":
        vertical = orientation == "vertical"
        problem_lines = textwrap.wrap(problem, width=27 if vertical else 48)
        max_lines = 3 if vertical else 2
        if len(problem_lines) > max_lines:
            problem_lines = problem_lines[:max_lines]
            problem_lines[-1] = problem_lines[-1].rstrip(" .,;:") + "..."
        return [
            {"type": "text", "id": "topic", "text": concept,
             "pos": [0.0, 4.8 if vertical else 2.7, 0],
             "color": "#F1C40F", "font_size": 27 if vertical else 30},
            {"type": "falling_energy", "id": "energy_model",
             "orientation": orientation, "period": 7.0,
             "energy_change": energy_change},
            {"type": "text", "id": "question_prompt",
             "text": "\n".join(problem_lines),
             "pos": [0.0, -4.5 if vertical else -3.0, 0],
             "color": "#B9C0CC", "font_size": 17 if vertical else 19},
        ]

    if orientation == "horizontal":
        centers = {"input": [-4.2, 0.0, 0], "principle": [0.0, 0.0, 0], "result": [4.2, 0.0, 0]}
        concept_pos = [0.0, 2.7, 0]
        question_pos = [0.0, -2.2, 0]
        arrow_pairs = [([-3.0, 0.0, 0], [-1.2, 0.0, 0]), ([1.2, 0.0, 0], [3.0, 0.0, 0])]
        concept_size = 30
        label_size = 21
        question_size = 19
        wrap_width = 48
        max_problem_lines = 2
    else:
        centers = {"input": [0.0, 2.0, 0], "principle": [0.0, 0.0, 0], "result": [0.0, -2.0, 0]}
        concept_pos = [0.0, 5.0, 0]
        question_pos = [0.0, -4.5, 0]
        arrow_pairs = [([0.0, 1.35, 0], [0.0, 0.65, 0]), ([0.0, -0.65, 0], [0.0, -1.35, 0])]
        concept_size = 26
        label_size = 22
        question_size = 17
        wrap_width = 27
        max_problem_lines = 3

    problem_lines = textwrap.wrap(problem, width=wrap_width) or [problem]
    if len(problem_lines) > max_problem_lines:
        problem_lines = problem_lines[:max_problem_lines]
        problem_lines[-1] = problem_lines[-1].rstrip(" .,;:") + "..."

    visuals = [
        {"type": "text", "id": "topic", "text": concept, "pos": concept_pos, "color": "#F1C40F", "font_size": concept_size},
        {"type": "circle", "kind": "circle", "id": "input", "pos": centers["input"], "radius": 0.62, "color": "#4CC9F0", "fill_opacity": 0.14},
        {"type": "text", "id": "input_label", "text": "QUESTION", "pos": centers["input"], "color": "#FFFFFF", "font_size": label_size},
        {"type": "circle", "kind": "circle", "id": "principle", "pos": centers["principle"], "radius": 0.78, "color": "#F1C40F", "fill_opacity": 0.16},
        {"type": "text", "id": "principle_label", "text": "CORE IDEA", "pos": centers["principle"], "color": "#F1C40F", "font_size": label_size},
        {"type": "circle", "kind": "circle", "id": "result", "pos": centers["result"], "radius": 0.62, "color": "#80ED99", "fill_opacity": 0.14},
        {"type": "text", "id": "result_label", "text": "RESULT", "pos": centers["result"], "color": "#FFFFFF", "font_size": label_size},
        {"type": "vector", "id": "input_to_idea", "start": arrow_pairs[0][0], "end": arrow_pairs[0][1], "color": "#4CC9F0"},
        {"type": "vector", "id": "idea_to_result", "start": arrow_pairs[1][0], "end": arrow_pairs[1][1], "color": "#80ED99"},
        {"type": "text", "id": "question_prompt", "text": "\n".join(problem_lines), "pos": question_pos, "color": "#B9C0CC", "font_size": question_size},
    ]
    return visuals

def _formula(concept: str, archetype: str = "concept_map",
             energy_change: float | None = None) -> list[str]:
    if archetype == "falling_energy":
        equations = [
            r"U_g = mgh",
            r"\Delta K = -\Delta U_g \quad \text{(no losses)}",
        ]
        if energy_change is not None:
            equations.append(rf"|\Delta U_g| = {energy_change:.1f}\ \text{{J}}")
        return equations
    return [r"\text{question} \xrightarrow{\text{principle}} \text{result}"]


def _beats(kind: str, archetype: str = "concept_map") -> list[dict]:
    if archetype == "falling_energy":
        sequence = (
            ["hook", "promise", "law", "experiment", "emphasis", "punchline"]
            if kind == "short"
            else ["hook", "promise", "law", "experiment", "midpoint", "emphasis", "punchline", "cta"]
        )
        return [{"type": beat_type, "focus": "energy_model"}
                for beat_type in sequence]

    if kind == "short":
        sequence = [
            ("hook", "input"),
            ("promise", "principle"),
            ("law", "principle"),
            ("experiment", "result"),
            ("emphasis", "input_to_idea"),
            ("punchline", "idea_to_result"),
        ]
    else:
        sequence = [
            ("hook", "input"),
            ("promise", "principle"),
            ("law", "principle"),
            ("experiment", "input_to_idea"),
            ("midpoint", "principle"),
            ("emphasis", "idea_to_result"),
            ("punchline", "result"),
            ("cta", "result"),
        ]
    transitions = {"promise": "push", "law": "wipe", "experiment": "push"}
    return [
        {
            "type": beat_type,
            "focus": focus,
            **({"transition": transitions[beat_type]}
               if beat_type in transitions else {}),
        }
        for beat_type, focus in sequence
    ]

def _short_script(concept: str, problem: str) -> str:
    return (
        f"Here is a useful way into {concept}. Do not begin by memorizing a formula. Ask what is changing and what must remain consistent. "
        f"Now make it concrete: {problem} Picture the situation first. Name the system, mark what is known, and state what the question asks for. "
        f"Connect those observations with one governing principle. That principle is the bridge from setup to result. Use only the quantities that matter, keep their units visible, and follow the logic one step at a time. "
        f"Finally, check the result against the picture. Does its direction make sense? Is its size plausible? If not, revisit the assumptions. "
        f"That is the intuition behind {concept}: see the structure, predict what should happen, and let the calculation test the prediction. A formula is useful when you know the story it tells."
    )


def _lecture_script(concept: str, problem: str) -> str:
    return (
        f"Let us build {concept} from an observation, not from a formula. A formula is a compact record of a relationship. To understand it, we need to know what the quantities mean, what assumptions are being made, and why those quantities belong together. "
        f"Here is the problem we will use: {problem} First, pause before calculating. Draw or imagine the situation. Decide what belongs inside the system and what is outside it. Mark the information supplied by the problem, then state exactly what we are trying to find. This prevents a familiar mistake: using every number simply because it is present. "
        f"Now ask the Feynman-style question: what is the simplest principle that could explain what we observe? For {concept}, the details depend on the specific system, so do not assume a law before checking that its conditions apply. Identify the relevant quantities and the relationship that links them. If a quantity is conserved, name the boundary of the system. If a force or influence acts, identify its direction and where it acts. If the problem describes a change, compare the initial and final states. "
        f"We can now organize the reasoning. Write the known values with units. Choose a relationship that matches the physical story. Rearrange it for the requested quantity, and substitute only after the structure is clear. Keep the units through the calculation; they are a second check on the algebra. For the example, the prompt provides the scenario, but a numerical answer requires the governing principle and any missing assumptions to be explicit. That distinction matters: a polished explanation should never pretend that unspecified information is known. "
        f"After calculating, translate the result back into ordinary language. Does the sign match the expected direction? Does the scale fit the situation? These checks turn a calculation into a model you can trust. "
        f"The visual summary is question, principle, result. The arrows are not decoration; they are the logic of the solution. Observe the setup, select a principle that truly applies, derive a prediction, and test it against the original picture. If the test fails, revise the model or the assumptions. "
        f"That is the lasting lesson of {concept}. Understanding is not repeating a sentence or copying symbols. It is being able to explain why the next step follows, and to notice when it does not. Once you can do that, a new problem is not a new ritual. It is a new situation whose structure you can investigate."
    )


def _energy_change(problem: str) -> float | None:
    mass = re.search(r"(\d+(?:\.\d+)?)\s*kg\b", problem, re.IGNORECASE)
    height = re.search(r"(\d+(?:\.\d+)?)\s*m\b", problem, re.IGNORECASE)
    if not mass or not height:
        return None
    return float(mass.group(1)) * 9.81 * float(height.group(1))


def _energy_fall_script(concept: str, problem: str, lecture: bool,
                        energy_change: float | None) -> str:
    answer = (
        f"That change has a magnitude of about {energy_change:.1f} joules. "
        if energy_change is not None else ""
    )
    if not lecture:
        return (
            f"Watch {concept} in this simple fall. {problem} At the top, the object and Earth have gravitational potential energy, m g h. As the object falls, its height decreases, so that stored energy goes down. Gravity speeds the object up, increasing its kinetic energy. "
            f"If we ignore air resistance, the loss in gravitational potential energy equals the gain in kinetic energy. {answer}The animation makes the accounting visible: the potential bar shrinks as the kinetic bar grows, while the total stays constant. "
            f"That result assumes air resistance is negligible; otherwise some mechanical energy becomes heat. "
            f"So do not memorize m g h alone. Identify the system, compare its starting and ending states, and follow where the energy goes. That is the useful idea behind {concept}."
        )
    return (
        f"Let us understand {concept} by following an object as it falls. Here is the question: {problem} Before calculating, decide what the system includes. We include the object and Earth together because gravitational potential energy belongs to their interaction. We also choose a reference height. The potential energy at any one point depends on that choice, but the change between two heights does not. "
        f"Near Earth's surface, gravitational potential energy is m g h. Mass is m, the gravitational field strength is g, and h is height above our reference. As the object descends, its gravitational potential energy decreases. Gravity does work on it, so its kinetic energy increases. If air resistance is negligible, mechanical energy is conserved: the decrease in potential energy equals the increase in kinetic energy. "
        f"For the supplied values, multiply the mass by g and by the vertical drop. {answer}Be precise about signs. A decrease in potential energy is a negative change; when a question asks for the loss, it usually wants the positive magnitude. The kinetic-energy gain has that same magnitude only under the no-loss assumption. "
        f"Watch the diagram. The object moves down while the potential-energy bar shrinks and the kinetic-energy bar grows. Their sum remains constant. The animation is an energy ledger, not decoration. If the bars do not balance, we have either omitted an energy store or included a transfer across the system boundary. "
        f"At the release point, if the object starts from rest, kinetic energy is zero and gravitational potential energy is largest. At the reference level, gravitational potential energy is zero by convention, while kinetic energy is largest in this ideal model. If it starts with a speed, include that initial kinetic energy too. "
        f"Real falls can involve air resistance. Then some mechanical energy becomes thermal energy in the object and air. Mechanical energy alone is no longer constant, but total energy remains conserved when we include those forms. Conservation is about the complete system, not one convenient pair of bars. "
        f"For any falling-body problem, identify the system, choose a reference, mark the height change, and state whether losses matter. Compare initial and final energy, then check the answer against the motion you pictured. The equation follows from the story; that is how {concept} becomes something you can explain rather than recite."
    )


def build_row(video_id: str, concept: str, problem: str, orientation: str, kind: str) -> dict:
    if kind == 'short':
        title = f"{concept} in One Minute"
        tagline = "The single idea that matters"
        question_text = problem
        audio_script = _short_script(concept, problem)
        correct_answer = "The idea is to find the governing constraint and follow it consistently."
    else:
        title = f"{concept}: A 3-Minute Lecture"
        tagline = "From intuition to worked example"
        question_text = problem
        audio_script = _lecture_script(concept, problem)
        correct_answer = "The concept explains why the system behaves as it does under the given constraint."

    topic_text = f"{concept} {problem}".lower()
    archetype = (
        "falling_energy"
        if any(word in topic_text for word in ("energy", "kinetic", "potential"))
        and re.search(r"\b(fall|falls|falling|drop|drops|dropped|descend|height)\b", topic_text)
        else "concept_map"
    )
    energy_change = _energy_change(problem) if archetype == "falling_energy" else None
    if archetype == "falling_energy":
        audio_script = _energy_fall_script(
            concept, problem, lecture=(kind == "lecture"),
            energy_change=energy_change,
        )
        correct_answer = (
            f"Potential energy decreases by {energy_change:.1f} J."
            if energy_change is not None else ""
        )

    row = {
        "video_id": video_id,
        "concept_type": "GENERIC",
        "header_title": title,
        "tagline": tagline,
        "question_text": question_text,
        "option_a": "",
        "option_b": "",
        "option_c": "",
        "option_d": "",
        "correct_answer": correct_answer if archetype == "falling_energy" else "",
        "equations_json": json.dumps(_formula(concept, archetype, energy_change)),
        "visual_data_json": json.dumps(
            _visuals(orientation, concept, problem, archetype, energy_change)),
        "beats_json": json.dumps(_beats(kind, archetype)),
        "audio_script": audio_script,
        "orientation": orientation,
        "target_duration_sec": 60 if kind == "short" else 180,
    }
    return row


def build_bundle(concept: str, problem: str, output_path: str | os.PathLike[str], kind: str = 'both') -> list[dict]:
    concept = concept.strip() or 'A General Concept'
    problem = problem.strip() or 'How does the system behave under its governing constraint?'
    variants = []
    target_kinds = ['short', 'lecture'] if kind == 'both' else [kind]

    for item in target_kinds:
        orientation = 'horizontal' if item == 'short' else 'vertical'
        video_id = f"{_slug(concept)}_{item}"
        variants.append(build_row(video_id, concept, problem, orientation, item))

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(variants)

    return variants


def main():
    parser = argparse.ArgumentParser(description='Generate a concept/problem CSV bundle for short and lecture outputs.')
    parser.add_argument('--concept', required=True, help='Topic or concept to explain.')
    parser.add_argument('--problem', required=True, help='Concrete scenario or question to solve.')
    parser.add_argument('--output', default='content_batch.csv', help='CSV path to write.')
    parser.add_argument('--kind', choices=['short', 'lecture', 'both'], default='both', help='Render style bundle to generate.')
    args = parser.parse_args()

    rows = build_bundle(args.concept, args.problem, args.output, args.kind)
    print(f'Wrote {len(rows)} row(s) to {args.output}')


if __name__ == '__main__':
    main()