#!/usr/bin/env python3

import argparse
import json
import math
import sqlite3
from pathlib import Path


MOTIVATION_KEYS = [f"Question {question}" for question in range(1, 29)]
SELF_EFFICACY_KEYS = [
    f"Self-Efficacy Question {question}" for question in range(1, 9)
]
GENAI_USAGE_KEYS = ["GenAI Question 1"]
USAGE_STYLE_KEYS = [f"GenAI Question {question}" for question in range(2, 7)]


def numeric_value(value):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            normalized = value.strip().lower()
            if normalized in ("true", "yes"):
                return 1.0
            if normalized in ("false", "no"):
                return 0.0
    return None


def variable_score(answers, keys):
    # Items with missing or nonnumeric values are ignored at the item level,
    # while a scale still returns a mean when at least one valid item exists.
    values = [numeric_value(answers.get(key)) for key in keys]
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else None


def pearson(first, second):
    # Pair observations before calculation so missing values in either variable
    # do not shift or mismatch participant records.
    pairs = [
        (x, y)
        for x, y in zip(first, second)
        if x is not None and y is not None
    ]
    if len(pairs) < 2:
        return None, len(pairs), None

    xs = [x for x, _ in pairs]
    ys = [y for _, y in pairs]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
    denominator = math.sqrt(
        sum((x - mean_x) ** 2 for x in xs)
        * sum((y - mean_y) ** 2 for y in ys)
    )

    if denominator == 0:
        return None, len(pairs), None

    correlation = numerator / denominator
    return correlation, len(pairs), significance(correlation, len(pairs))


def betai(a, b, x):
    """Regularized incomplete beta function."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0

    factor = math.exp(
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log1p(-x)
    )
    if x < (a + 1) / (a + b + 2):
        return factor * beta_continued_fraction(a, b, x) / a

    return 1 - factor * beta_continued_fraction(b, a, 1 - x) / b


def beta_continued_fraction(a, b, x):
    maximum_iterations = 200
    epsilon = 3e-14
    minimum = 1e-300
    qab = a + b
    qap = a + 1
    qam = a - 1
    c = 1.0
    d = 1 - qab * x / qap
    d = minimum if abs(d) < minimum else d
    d = 1 / d
    result = d

    for iteration in range(1, maximum_iterations + 1):
        even_index = 2 * iteration
        coefficient = even_index * (b - iteration) * x / (
            (qam + even_index) * (a + even_index)
        )
        d = 1 + coefficient * d
        d = minimum if abs(d) < minimum else d
        c = 1 + coefficient / c
        c = minimum if abs(c) < minimum else c
        d = 1 / d
        result *= d * c

        coefficient = -(a + iteration) * (qab + iteration) * x / (
            (a + even_index) * (qap + even_index)
        )
        d = 1 + coefficient * d
        d = minimum if abs(d) < minimum else d
        c = 1 + coefficient / c
        c = minimum if abs(c) < minimum else c
        d = 1 / d
        delta = d * c
        result *= delta
        if abs(delta - 1) < epsilon:
            break

    return result


def significance(correlation, sample_size):
    # Convert Pearson r to a two-tailed t test. This avoids adding SciPy as a
    # required runtime dependency while reporting the same statistic.
    degrees_of_freedom = sample_size - 2
    correlation = max(-1.0, min(1.0, correlation))
    if correlation == 1.0 or correlation == -1.0:
        return 0.0
    if degrees_of_freedom <= 0:
        return None

    t_squared = correlation * correlation * degrees_of_freedom / (
        1 - correlation * correlation
    )
    x = degrees_of_freedom / (degrees_of_freedom + t_squared)
    return betai(degrees_of_freedom / 2, 0.5, x)


def format_result(correlation, p_value):
    if correlation is None:
        return "-"
    if p_value is None:
        return f"{correlation:.3f}"
    return f"{correlation:.3f} (p={p_value:.4f})"


def usage_style_value(value):
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("true", "yes", "always"):
            return 2.0 if normalized == "always" else 1.0
        if normalized in ("false", "no", "never"):
            return 0.0
        if normalized == "sometimes":
            return 1.0
    numeric = numeric_value(value)
    return numeric


def mean(values):
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else None


def format_mean(values):
    value = mean(values)
    return "n/a" if value is None else f"{value:.3f}"


def usage_group(usage, high_cutoff):
    return "High Usage" if usage is not None and usage > high_cutoff else "Average Usage"


def print_usage_report(parsed_answers, high_cutoff):
    # The frequency question is a 1-7 usage measure; participants above the
    # cutoff are reported separately without discarding their style responses.
    groups = {"Average Usage": [], "High Usage": []}
    for answers in parsed_answers:
        usage = numeric_value(answers.get("GenAI Question 1"))
        if usage is not None:
            groups[usage_group(usage, high_cutoff)].append(answers)

    print("\nUsage-frequency groups")
    print(f"Split: Average <= {high_cutoff:g}; High > {high_cutoff:g}")
    for group_name, answers in groups.items():
        motivation_scores = [
            variable_score(answer, MOTIVATION_KEYS) for answer in answers
        ]
        efficacy_scores = [
            variable_score(answer, SELF_EFFICACY_KEYS) for answer in answers
        ]
        usage_scores = [numeric_value(answer.get("GenAI Question 1")) for answer in answers]
        print(
            f"{group_name}: n={len(answers)}, "
            f"usage_mean={format_mean(usage_scores)} "
            f"motivation_mean={format_mean(motivation_scores)} "
            f"efficacy_mean={format_mean(efficacy_scores)}"
        )

    print("\nUsage-style means by group")
    print("Coding: False/No/Never=0, True/Yes/Sometimes=1, Always=2")
    for question_key in USAGE_STYLE_KEYS:
        print(question_key)
        for group_name in groups:
            values = [
                usage_style_value(answer.get(question_key))
                for answer in groups[group_name]
            ]
            print(f"  {group_name}: n={len([v for v in values if v is not None])}, "
                  f"mean={format_mean(values)}")

    print("\nUsage styles correlated with motivation and self-efficacy")
    for question_key in USAGE_STYLE_KEYS:
        style_values = [
            usage_style_value(answer.get(question_key))
            for answer in parsed_answers
        ]
        motivation_values = [
            variable_score(answer, MOTIVATION_KEYS)
            for answer in parsed_answers
        ]
        efficacy_values = [
            variable_score(answer, SELF_EFFICACY_KEYS)
            for answer in parsed_answers
        ]
        motivation_r = pearson(style_values, motivation_values)
        efficacy_r = pearson(style_values, efficacy_values)
        print(
            f"{question_key}: motivation {format_result(*motivation_r[::2])}; "
            f"self-efficacy {format_result(*efficacy_r[::2])}"
        )


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Calculate Pearson r between two survey question averages."
    )
    parser.add_argument("--database", default="data/survey.sqlite")
    parser.add_argument("--x", nargs="+", help="Keys for the X variable.")
    parser.add_argument("--y", nargs="+", help="Keys for the Y variable.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Compare the core Self-Efficacy, School Motivation, and GenAI Usage variables.",
    )
    parser.add_argument(
        "--usage-report",
        action="store_true",
        help="Compare average/high GenAI usage groups and usage styles.",
    )
    parser.add_argument(
        "--high-usage-cutoff",
        type=float,
        default=4.5,
        help="GenAI Question 1 values above this cutoff are high usage.",
    )
    return parser.parse_args()


def main():
    # SQLite contains the full JSON payload, which keeps the analysis script
    # synchronized with new or renamed questionnaire keys.
    args = parse_arguments()
    connection = sqlite3.connect(Path(args.database))
    rows = connection.execute("SELECT answers FROM survey_responses").fetchall()
    parsed_answers = [
        json.loads(answers_json)
        for (answers_json,) in rows
    ]

    if args.usage_report:
        print_usage_report(parsed_answers, args.high_usage_cutoff)

        motivation_values = [
            variable_score(answers, MOTIVATION_KEYS)
            for answers in parsed_answers
        ]
        efficacy_values = [
            variable_score(answers, SELF_EFFICACY_KEYS)
            for answers in parsed_answers
        ]
        correlation, sample_size, p_value = pearson(
            motivation_values, efficacy_values
        )
        print("\nSchool Motivation vs. Self-Efficacy")
        print(f"n: {sample_size}")
        print("r: constant" if correlation is None else f"r: {correlation:.4f}")
        print("p: not available" if p_value is None else f"p: {p_value:.4f}")
        connection.close()
        return

    if args.all:
        variables = [
            ("Self-Efficacy", SELF_EFFICACY_KEYS),
            ("School Motivation", MOTIVATION_KEYS),
            ("GenAI Usage", GENAI_USAGE_KEYS),
        ]
        print("\t" + "\t".join(name for name, _ in variables))
        for x_name, x_keys in variables:
            results = []
            for _, y_keys in variables:
                x_values = [
                    variable_score(answers, x_keys)
                    for answers in parsed_answers
                ]
                y_values = [
                    variable_score(answers, y_keys)
                    for answers in parsed_answers
                ]
                correlation, _, p_value = pearson(x_values, y_values)
                results.append(format_result(correlation, p_value))
            print("\t".join([x_name] + results))
        connection.close()
        return

    if not args.x or not args.y:
        print("Use --x and --y, or use --all.")
        connection.close()
        return

    first = []
    second = []
    for (answers_json,) in rows:
        answers = json.loads(answers_json)
        first.append(variable_score(answers, args.x))
        second.append(variable_score(answers, args.y))

    correlation, sample_size, p_value = pearson(first, second)
    connection.close()

    print(f"X: {', '.join(args.x)}")
    print(f"Y: {', '.join(args.y)}")
    print(f"n: {sample_size}")
    print("r: constant" if correlation is None else f"r: {correlation:.4f}")
    print("p: not available" if p_value is None else f"p: {p_value:.4f}")


if __name__ == "__main__":
    main()
