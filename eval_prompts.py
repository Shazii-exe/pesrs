"""
eval_prompts.py
75 evaluation prompts across 5 routes × 3 quality tiers.

Each prompt has:
  - text:           the actual prompt
  - route:          expected route (ground truth)
  - quality:        "clean" | "borderline" | "messy"
  - expected_gate:  "pass" (direct answer) | "rewrite" (should trigger enhancement)
  - notes:          what makes it clean/messy/borderline
"""

EVAL_PROMPTS = [

    # ─────────────────────────────────────────────
    # SOCIAL  (15 prompts)
    # ─────────────────────────────────────────────

    # Clean — clear greeting, no rewrite needed
    {"id": "S01", "route": "SOCIAL", "quality": "clean",       "expected_gate": "pass",
     "text": "Hey!",
     "notes": "Simple greeting"},

    {"id": "S02", "route": "SOCIAL", "quality": "clean",       "expected_gate": "pass",
     "text": "Good morning!",
     "notes": "Standard greeting"},

    {"id": "S03", "route": "SOCIAL", "quality": "clean",       "expected_gate": "pass",
     "text": "How are you doing today?",
     "notes": "Casual check-in"},

    {"id": "S04", "route": "SOCIAL", "quality": "clean",       "expected_gate": "pass",
     "text": "Thanks for the help earlier!",
     "notes": "Appreciation message"},

    {"id": "S05", "route": "SOCIAL", "quality": "clean",       "expected_gate": "pass",
     "text": "That was really useful, thank you.",
     "notes": "Positive social feedback"},

    # Borderline — social but slightly ambiguous
    {"id": "S06", "route": "SOCIAL", "quality": "borderline",  "expected_gate": "pass",
     "text": "hey can you help",
     "notes": "Vague but social opener"},

    {"id": "S07", "route": "SOCIAL", "quality": "borderline",  "expected_gate": "pass",
     "text": "yo whats good",
     "notes": "Informal greeting"},

    {"id": "S08", "route": "SOCIAL", "quality": "borderline",  "expected_gate": "pass",
     "text": "hi i need something",
     "notes": "Social opener with vague intent"},

    {"id": "S09", "route": "SOCIAL", "quality": "borderline",  "expected_gate": "pass",
     "text": "hello, i was wondering if you could assist me",
     "notes": "Polite opener without specifics"},

    {"id": "S10", "route": "SOCIAL", "quality": "borderline",  "expected_gate": "pass",
     "text": "hey are you there?",
     "notes": "Checking presence"},

    # Messy — social but garbled
    {"id": "S11", "route": "SOCIAL", "quality": "messy",       "expected_gate": "pass",
     "text": "heyy gm hru lol",
     "notes": "Heavy abbreviation/slang greeting"},

    {"id": "S12", "route": "SOCIAL", "quality": "messy",       "expected_gate": "pass",
     "text": "sup bro hope ur gud",
     "notes": "Casual slangy greeting"},

    {"id": "S13", "route": "SOCIAL", "quality": "messy",       "expected_gate": "pass",
     "text": "yo!! just checking in how r things",
     "notes": "Informal check-in"},

    {"id": "S14", "route": "SOCIAL", "quality": "messy",       "expected_gate": "pass",
     "text": "hi there!! doing good? hope everything is fine on ur end",
     "notes": "Casual social opener"},

    {"id": "S15", "route": "SOCIAL", "quality": "messy",       "expected_gate": "pass",
     "text": "hiii just wanted to say thanks for everything!!",
     "notes": "Social appreciation message"},

    # ─────────────────────────────────────────────
    # QA  (15 prompts)
    # ─────────────────────────────────────────────

    # Clean
    {"id": "Q01", "route": "QA", "quality": "clean",           "expected_gate": "pass",
     "text": "What is the difference between supervised and unsupervised learning?",
     "notes": "Clear, specific question"},

    {"id": "Q02", "route": "QA", "quality": "clean",           "expected_gate": "pass",
     "text": "What causes inflation in an economy?",
     "notes": "Clear economics question"},

    {"id": "Q03", "route": "QA", "quality": "clean",           "expected_gate": "pass",
     "text": "What is the difference between RAM and ROM in a computer?",
     "notes": "Clear technical question"},

    {"id": "Q04", "route": "QA", "quality": "clean",           "expected_gate": "pass",
     "text": "How does the human immune system respond to a virus?",
     "notes": "Clear biology question"},

    {"id": "Q05", "route": "QA", "quality": "clean",           "expected_gate": "pass",
     "text": "What is the capital of Australia and what is it known for?",
     "notes": "Two-part factual question"},

    # Borderline
    {"id": "Q06", "route": "QA", "quality": "borderline",      "expected_gate": "rewrite",
     "text": "explain machine learning but simple",
     "notes": "Missing audience/depth context"},

    {"id": "Q07", "route": "QA", "quality": "borderline",      "expected_gate": "rewrite",
     "text": "what does REST mean in software",
     "notes": "Slightly informal but mostly clear"},

    {"id": "Q08", "route": "QA", "quality": "borderline",      "expected_gate": "rewrite",
     "text": "how is ai different from normal programming",
     "notes": "Vague comparison, needs scope"},

    {"id": "Q09", "route": "QA", "quality": "borderline",      "expected_gate": "rewrite",
     "text": "tell me about blockchain",
     "notes": "Very broad, no scope or depth specified"},

    {"id": "Q10", "route": "QA", "quality": "borderline",      "expected_gate": "rewrite",
     "text": "whats the point of version control",
     "notes": "Informal phrasing, reasonable intent"},

    # Messy
    {"id": "Q11", "route": "QA", "quality": "messy",           "expected_gate": "rewrite",
     "text": "explain me machine learning but like simple not too technical and give example also",
     "notes": "Run-on, informal, vague depth"},

    {"id": "Q12", "route": "QA", "quality": "messy",           "expected_gate": "rewrite",
     "text": "idk how neural networks work can u explain",
     "notes": "Informal, no depth or context"},

    {"id": "Q13", "route": "QA", "quality": "messy",           "expected_gate": "rewrite",
     "text": "what is gpt and how it works and why everyone using it",
     "notes": "Multiple questions run together"},

    {"id": "Q14", "route": "QA", "quality": "messy",           "expected_gate": "rewrite",
     "text": "difference between deep learning machine learning ai all those things",
     "notes": "Vague comparison, no structure"},

    {"id": "Q15", "route": "QA", "quality": "messy",           "expected_gate": "rewrite",
     "text": "why do some countries have more inflation idk economics help",
     "notes": "Incomplete thought, no framing"},

    # ─────────────────────────────────────────────
    # TASK  (15 prompts)
    # ─────────────────────────────────────────────

    # Clean
    {"id": "T01", "route": "TASK", "quality": "clean",         "expected_gate": "pass",
     "text": "Write a professional email to a client explaining that their project delivery will be delayed by one week due to unexpected technical issues.",
     "notes": "Clear task with constraints"},

    {"id": "T02", "route": "TASK", "quality": "clean",         "expected_gate": "pass",
     "text": "Create a 5-day meal plan for a vegetarian person with a daily calorie target of 1800 kcal.",
     "notes": "Specific task with constraints"},

    {"id": "T03", "route": "TASK", "quality": "clean",         "expected_gate": "pass",
     "text": "Summarize the following research abstract in 3 bullet points for a non-technical audience.",
     "notes": "Clear task with audience and format"},

    {"id": "T04", "route": "TASK", "quality": "clean",         "expected_gate": "pass",
     "text": "Compare the pros and cons of working remotely vs in-office in a table format.",
     "notes": "Clear comparison task with format"},

    {"id": "T05", "route": "TASK", "quality": "clean",         "expected_gate": "pass",
     "text": "Draft a LinkedIn post announcing that I just completed my MBA, keeping it professional but warm.",
     "notes": "Clear task with tone constraint"},

    # Borderline
    {"id": "T06", "route": "TASK", "quality": "borderline",    "expected_gate": "rewrite",
     "text": "write something for my presentation about climate change",
     "notes": "Missing format, length, audience"},

    {"id": "T07", "route": "TASK", "quality": "borderline",    "expected_gate": "rewrite",
     "text": "make a plan for my startup",
     "notes": "Too broad, no industry or stage"},

    {"id": "T08", "route": "TASK", "quality": "borderline",    "expected_gate": "rewrite",
     "text": "help me write a cover letter for a tech job",
     "notes": "Missing role, company, experience details"},

    {"id": "T09", "route": "TASK", "quality": "borderline",    "expected_gate": "rewrite",
     "text": "give me a social media strategy",
     "notes": "Missing platform, goal, audience"},

    {"id": "T10", "route": "TASK", "quality": "borderline",    "expected_gate": "rewrite",
     "text": "review my business plan and give feedback",
     "notes": "No plan attached, missing criteria"},

    # Messy
    {"id": "T11", "route": "TASK", "quality": "messy",         "expected_gate": "rewrite",
     "text": "i need help with my presentation thing for tomorrow its about climate idk how to make it good",
     "notes": "Vague, missing format and scope"},

    {"id": "T12", "route": "TASK", "quality": "messy",         "expected_gate": "rewrite",
     "text": "my boss wants report on sales q3 vs q4 i have numbers but dont know how to structure it help",
     "notes": "Missing structure, no data provided"},

    {"id": "T13", "route": "TASK", "quality": "messy",         "expected_gate": "rewrite",
     "text": "write email to client they angry about delay but its not our fault actually",
     "notes": "Vague, emotional framing, missing details"},

    {"id": "T14", "route": "TASK", "quality": "messy",         "expected_gate": "rewrite",
     "text": "make something that explains our product to investors we need funding",
     "notes": "No product info, audience unclear"},

    {"id": "T15", "route": "TASK", "quality": "messy",         "expected_gate": "rewrite",
     "text": "i have to do a report for uni about sustainability but idk where to start or what to include",
     "notes": "Missing scope, word count, focus"},

    # ─────────────────────────────────────────────
    # TECH  (15 prompts)
    # ─────────────────────────────────────────────

    # Clean
    {"id": "X01", "route": "TECH", "quality": "clean",         "expected_gate": "pass",
     "text": "Write a Python function that takes a list of integers and returns the top 3 largest values without using sort().",
     "notes": "Clear, constrained coding task"},

    {"id": "X02", "route": "TECH", "quality": "clean",         "expected_gate": "pass",
     "text": "What are the main differences between REST and GraphQL APIs? Include pros and cons of each.",
     "notes": "Clear technical comparison question"},

    {"id": "X03", "route": "TECH", "quality": "clean",         "expected_gate": "pass",
     "text": "Write a SQL query to find the top 5 customers by total purchase amount from a table called orders with columns customer_id, order_date, and amount.",
     "notes": "Clear SQL task with schema"},

    {"id": "X04", "route": "TECH", "quality": "clean",         "expected_gate": "pass",
     "text": "Explain what Docker volumes are and when to use them instead of bind mounts.",
     "notes": "Clear technical explanation request"},

    {"id": "X05", "route": "TECH", "quality": "clean",         "expected_gate": "pass",
     "text": "How do I implement rate limiting in a FastAPI application using a Redis backend?",
     "notes": "Specific implementation question with stack"},

    # Borderline
    {"id": "X06", "route": "TECH", "quality": "borderline",    "expected_gate": "rewrite",
     "text": "how to make my python code faster",
     "notes": "Missing code, no context"},

    {"id": "X07", "route": "TECH", "quality": "borderline",    "expected_gate": "rewrite",
     "text": "my api is slow what should i do",
     "notes": "No stack, no specifics"},

    {"id": "X08", "route": "TECH", "quality": "borderline",    "expected_gate": "rewrite",
     "text": "explain async await in javascript",
     "notes": "Reasonable but missing depth/audience"},

    {"id": "X09", "route": "TECH", "quality": "borderline",    "expected_gate": "rewrite",
     "text": "write a function to validate email address",
     "notes": "Missing language and validation rules"},

    {"id": "X10", "route": "TECH", "quality": "borderline",    "expected_gate": "rewrite",
     "text": "how to connect to a database in python",
     "notes": "Missing which database"},

    # Messy
    {"id": "X11", "route": "TECH", "quality": "messy",         "expected_gate": "rewrite",
     "text": "my code keeps crashing idk why can u help its python something about index error",
     "notes": "No code, vague error description"},

    {"id": "X12", "route": "TECH", "quality": "messy",         "expected_gate": "rewrite",
     "text": "need to build something that scrapes a website and saves data somewhere help",
     "notes": "Vague stack, no target site or schema"},

    {"id": "X13", "route": "TECH", "quality": "messy",         "expected_gate": "rewrite",
     "text": "my streamlit app is slow when loading data how to fix pls",
     "notes": "No code, no data size, no context"},

    {"id": "X14", "route": "TECH", "quality": "messy",         "expected_gate": "rewrite",
     "text": "write me code for a login system with users and passwords and stuff",
     "notes": "Vague stack, no security requirements"},

    {"id": "X15", "route": "TECH", "quality": "messy",         "expected_gate": "rewrite",
     "text": "i have a pandas dataframe and need to do some analysis but idk what functions to use",
     "notes": "No data description, no analysis goal"},

    # ─────────────────────────────────────────────
    # CREATIVE  (15 prompts)
    # ─────────────────────────────────────────────

    # Clean
    {"id": "C01", "route": "CREATIVE", "quality": "clean",     "expected_gate": "pass",
     "text": "Write a short poem about the feeling of watching rain from a window on a quiet afternoon.",
     "notes": "Clear creative prompt with mood"},

    {"id": "C02", "route": "CREATIVE", "quality": "clean",     "expected_gate": "pass",
     "text": "Write a 200-word opening paragraph for a science fiction story set on a colony ship 200 years into a 500-year journey to another star.",
     "notes": "Well-defined creative task with constraints"},

    {"id": "C03", "route": "CREATIVE", "quality": "clean",     "expected_gate": "pass",
     "text": "Generate 5 unique startup name ideas for an AI-powered personal finance app targeting millennials.",
     "notes": "Clear creative task with constraints"},

    {"id": "C04", "route": "CREATIVE", "quality": "clean",     "expected_gate": "pass",
     "text": "Write a villain character description for a fantasy novel — morally complex, not purely evil.",
     "notes": "Clear creative brief with constraint"},

    {"id": "C05", "route": "CREATIVE", "quality": "clean",     "expected_gate": "pass",
     "text": "Brainstorm 10 unconventional marketing campaign ideas for a sustainable clothing brand targeting Gen Z.",
     "notes": "Clear creative task with audience"},

    # Borderline
    {"id": "C06", "route": "CREATIVE", "quality": "borderline","expected_gate": "pass",
     "text": "write me a short story",
     "notes": "Vague but creative prompts can work with defaults"},

    {"id": "C07", "route": "CREATIVE", "quality": "borderline","expected_gate": "pass",
     "text": "give me some business name ideas",
     "notes": "Missing industry but workable"},

    {"id": "C08", "route": "CREATIVE", "quality": "borderline","expected_gate": "rewrite",
     "text": "write something creative for my brand",
     "notes": "Too vague — no brand info"},

    {"id": "C09", "route": "CREATIVE", "quality": "borderline","expected_gate": "pass",
     "text": "come up with a plot twist for a thriller",
     "notes": "Vague but genre is clear"},

    {"id": "C10", "route": "CREATIVE", "quality": "borderline","expected_gate": "rewrite",
     "text": "make something funny",
     "notes": "No context, no format, no audience"},

    # Messy
    {"id": "C11", "route": "CREATIVE", "quality": "messy",     "expected_gate": "rewrite",
     "text": "i need a story for my project idk what kind just something interesting maybe sci fi or not",
     "notes": "Contradictory, no scope"},

    {"id": "C12", "route": "CREATIVE", "quality": "messy",     "expected_gate": "rewrite",
     "text": "write a rap about my uni life its stressful but also fun sometimes idk just make it cool",
     "notes": "Vague brief, no length or style"},

    {"id": "C13", "route": "CREATIVE", "quality": "messy",     "expected_gate": "rewrite",
     "text": "help me brainstorm app ideas we have a hackathon and idk what to build",
     "notes": "Missing theme, constraints, team size"},

    {"id": "C14", "route": "CREATIVE", "quality": "messy",     "expected_gate": "rewrite",
     "text": "write a tagline for my startup its about health and tech and stuff",
     "notes": "No brand name, no differentiator"},

    {"id": "C15", "route": "CREATIVE", "quality": "messy",     "expected_gate": "rewrite",
     "text": "make a character for a game idk like a hero or villain or something cool",
     "notes": "No genre, no constraints, no direction"},
]
