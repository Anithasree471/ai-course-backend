import os
import json
import re
import requests
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def extract_json(text):
    text = text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text)
    except:
        pass

    match = re.search(r"\[.*\]|\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())

    raise ValueError("No valid JSON found")


def ask_ai(prompt):
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.1-8b-instant",
        temperature=0.4
    )
    return response.choices[0].message.content.strip()


def is_programming_topic(topic):
    topic = topic.lower().strip()

    programming_keywords = [
        "python", "java", "c", "c++", "javascript", "js", "react", "node",
        "express", "html", "css", "sql", "mysql", "mongodb", "flask",
        "django", "php", "programming", "coding", "web development",
        "software", "api", "data structure", "data structures", "algorithm",
        "algorithms", "machine learning", "artificial intelligence", "dbms"
    ]

    return any(word in topic for word in programming_keywords)


def get_youtube_videos(topic):
    api_key = os.getenv("YOUTUBE_API_KEY")

    if not api_key:
        return [
            {
                "title": f"{topic} Tutorial",
                "videoId": "",
                "url": f"https://www.youtube.com/results?search_query={topic.replace(' ', '+')}+tutorial"
            }
        ]

    url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "key": api_key,
        "q": f"{topic} tutorial for beginners in english",
        "part": "snippet",
        "type": "video",
        "maxResults": 3,
        "videoEmbeddable": "true",
        "safeSearch": "strict",
        "order": "relevance"
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        videos = []

        for item in data.get("items", []):
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]

            videos.append({
                "title": title,
                "videoId": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}"
            })

        return videos

    except Exception as e:
        print("YouTube fetch error:", e)
        return [
            {
                "title": f"{topic} Tutorial",
                "videoId": "",
                "url": f"https://www.youtube.com/results?search_query={topic.replace(' ', '+')}+tutorial"
            }
        ]


def generate_module_titles(topic):
    prompt = f"""
Generate exactly 5 beginner-friendly module titles for a course on {topic}.

Return ONLY valid JSON array like this:
[
  "Module title 1",
  "Module title 2",
  "Module title 3",
  "Module title 4",
  "Module title 5"
]

Rules:
- Titles must be specific to {topic}
- Do not use generic titles like "Core Concepts" unless really needed
- If the topic is programming, include real concepts like syntax, variables, loops, functions, OOP, arrays, linked list, stack, queue, etc where relevant
"""

    try:
        result = ask_ai(prompt)
        titles = extract_json(result)
        if isinstance(titles, list) and len(titles) == 5:
            return titles
    except Exception as e:
        print("Module title generation failed:", e)

    return [
        f"Introduction to {topic}",
        f"Basic Concepts of {topic}",
        f"Intermediate {topic}",
        f"Advanced {topic}",
        f"Applications of {topic}"
    ]


def generate_module_content(topic, module_title):
    prompt = f"""
You are a teacher.

Write detailed study notes for the course topic "{topic}" and module "{module_title}".

Rules:
- Make it specific to {topic}
- Do not write generic lines like "this is an important subject"
- Do not repeat the module title again at the top
- Do not use markdown headings like ### or bold markers like **
- If code is needed, place it inside triple backticks
- Write like real teaching material for a student
- Use this clean structure:

1. Introduction
2. Explanation
3. Important Points
4. Example
5. Summary

- Use simple beginner-friendly language
- Write around 250 to 400 words
- Return plain text only
"""

    try:
        return ask_ai(prompt)
    except Exception as e:
        print("Module content generation failed:", e)
        return f"""1. Introduction

{module_title} is an important part of {topic}.

2. Explanation

This module explains the basic concept of {module_title} in {topic}.

3. Important Points

- Understand the definition
- Learn the usage
- Study examples

4. Example

A simple example can be used to understand {module_title} in {topic}.

5. Summary

This module gives a foundation for learning {topic}."""


def generate_mcq(topic, modules):
    notes_text = ""

    for m in modules:
        notes_text += f"\nModule: {m['title']}\n"
        notes_text += m["content"] + "\n"

    prompt = f"""
You are creating an assessment for a course.

Use the study notes below to generate questions.

COURSE NOTES:
{notes_text}

Create exactly 10 multiple choice questions.

Rules:
- Questions MUST come from the notes above
- Do not create random questions
- Test understanding of the concepts explained
- Each question must have 4 options
- Only one correct answer
- Use simple student-friendly language

Return ONLY valid JSON like this:

[
  {{
    "question": "Question text",
    "options": ["A", "B", "C", "D"],
    "answer": "Correct option text"
  }}
]
"""

    try:
        result = ask_ai(prompt)
        mcq = extract_json(result)

        if isinstance(mcq, list) and len(mcq) >= 10:
            return mcq[:10]

    except Exception as e:
        print("MCQ generation failed:", e)

    return []


def generate_assignment(topic, modules):
    notes_text = ""

    for m in modules:
        notes_text += f"\nModule: {m['title']}\n"
        notes_text += m["content"] + "\n"

    prompt = f"""
You are creating a programming practice problem for students.

Use the course notes below to design a coding problem.

COURSE NOTES:
{notes_text}

Create ONE beginner-to-intermediate coding problem.

Rules:
- The problem must relate to the concepts taught in the notes
- Keep it beginner friendly
- The question must be solvable with basic programming
- Provide a clear problem statement
- Provide a sample input
- Provide a sample output
- Provide a short explanation

Return ONLY valid JSON in this format:

{{
  "problem": "Clear coding problem description",
  "input": "Example input",
  "output": "Expected output",
  "explanation": "Short explanation of the solution idea"
}}
"""

    try:
        result = ask_ai(prompt)
        assignment = extract_json(result)

        if isinstance(assignment, dict):
            return assignment

    except Exception as e:
        print("Assignment generation failed:", e)

    return {
        "problem": f"""
Write a program in {topic} that takes an integer n and prints numbers from 1 to n.
""",
        "input": "5",
        "output": "1 2 3 4 5",
        "explanation": "Use a loop to print numbers from 1 up to the given number."
    }


def get_w3schools_url(topic):
    t = topic.lower().strip()

    mapping = {
        "python": "https://www.w3schools.com/python/",
        "java": "https://www.w3schools.com/java/",
        "c": "https://www.w3schools.com/c/",
        "c++": "https://www.w3schools.com/cpp/",
        "javascript": "https://www.w3schools.com/js/",
        "html": "https://www.w3schools.com/html/",
        "css": "https://www.w3schools.com/css/",
        "sql": "https://www.w3schools.com/sql/",
        "react": "https://www.w3schools.com/react/",
        "mongodb": "https://www.w3schools.com/mongodb/",
        "data structure": "https://www.w3schools.com/dsa/",
        "data structures": "https://www.w3schools.com/dsa/"
    }

    return mapping.get(t, f"https://www.w3schools.com/search/search.asp?q={topic}")


def get_gfg_url(topic):
    t = topic.lower().strip()

    mapping = {
        "python": "https://www.geeksforgeeks.org/python/python-programming-language-tutorial/",
        "java": "https://www.geeksforgeeks.org/java/",
        "c": "https://www.geeksforgeeks.org/c-programming-language/",
        "c++": "https://www.geeksforgeeks.org/c-plus-plus/",
        "javascript": "https://www.geeksforgeeks.org/javascript/",
        "html": "https://www.geeksforgeeks.org/html-tutorial/",
        "css": "https://www.geeksforgeeks.org/css-tutorial/",
        "sql": "https://www.geeksforgeeks.org/sql-tutorial/",
        "react": "https://www.geeksforgeeks.org/reactjs-tutorials/",
        "mongodb": "https://www.geeksforgeeks.org/mongodb-an-introduction/",
        "data structure": "https://www.geeksforgeeks.org/data-structures/",
        "data structures": "https://www.geeksforgeeks.org/data-structures/"
    }

    return mapping.get(t, f"https://www.geeksforgeeks.org/?s={topic.replace(' ', '+')}")


def get_wikipedia_url(topic):
    return f"https://en.wikipedia.org/wiki/Special:Search?search={topic.replace(' ', '+')}"


def generate_course(topic):
    module_titles = generate_module_titles(topic)

    modules = []
    for title in module_titles:
        content = generate_module_content(topic, title)
        modules.append({
            "title": title,
            "content": content
        })

    mcq = generate_mcq(topic, modules)
    is_programming = is_programming_topic(topic)

    assignment = None
    if is_programming:
        assignment = generate_assignment(topic, modules)

    youtube = get_youtube_videos(topic)

    if is_programming:
        articles = [
            {
                "title": "W3Schools",
                "url": get_w3schools_url(topic)
            },
            {
                "title": "GeeksforGeeks",
                "url": get_gfg_url(topic)
            },
            {
                "title": "Wikipedia",
                "url": get_wikipedia_url(topic)
            }
        ]
    else:
        articles = [
            {
                "title": "Wikipedia",
                "url": get_wikipedia_url(topic)
            },
            {
                "title": "Britannica",
                "url": f"https://www.britannica.com/search?query={topic.replace(' ', '+')}"
            },
            {
                "title": "Google Search",
                "url": f"https://www.google.com/search?q={topic.replace(' ', '+')}+article"
            }
        ]

    return {
        "title": f"{topic} Course",
        "modules": modules,
        "mcq": mcq,
        "assignment": assignment,
        "isProgramming": is_programming,
        "youtube": youtube,
        "articles": articles
    }