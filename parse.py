import re
import json

PDF_PATH = '/Users/ayaandave/Downloads/e13482c8-73a7-4ae8-8b2f-65e52dc07185_sat-reading.pdf'
TXT_CACHE = '/tmp/rw_pdfplumber.txt'

DOMAINS = [
    "Standard English Conventions",
    "Information and Ideas",
    "Craft and Structure",
    "Expression of Ideas",
]
SKILLS = [
    "Central Ideas and Details",
    "Command of Evidence",
    "Cross-Text Connections",
    "Text Structure and Purpose",
    "Rhetorical Synthesis",
    "Form, Structure, and Sense",
    "Words in Context",
    "Transitions",
    "Boundaries",
    "Inferences",
]

def extract_text():
    import os
    if os.path.exists(TXT_CACHE):
        return open(TXT_CACHE, encoding='utf-8').read()
    import pdfplumber
    texts = []
    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages:
            texts.append(page.extract_text(use_text_flow=True) or '')
    full = '\n'.join(texts)
    with open(TXT_CACHE, 'w', encoding='utf-8') as f:
        f.write(full)
    return full

def split_blocks(text):
    parts = re.split(r'Question ID (\w+)', text)[1:]
    return list(zip(parts[0::2], parts[1::2]))

def norm(s):
    return re.sub(r'\s+', ' ', s).strip()

def parse_metadata(block):
    m = re.search(r'Reading and Writing\s*\nDomain\s*\n(.*?)\nSkill\s*\n(.*?)\nDifficulty', block, re.DOTALL)
    if not m:
        return {}
    domain = norm(m.group(1))
    skill = norm(m.group(2))
    result = {}
    if domain in DOMAINS:
        result['domain'] = domain
    if skill in SKILLS:
        result['skill'] = skill
    dm = re.search(r'Question Difficulty:\s*(Easy|Medium|Hard)', block)
    if dm:
        result['difficulty'] = dm.group(1)
    return result

def parse_question_and_choices(qid, block):
    id_marks = [m.start() for m in re.finditer(rf'ID:\s*{re.escape(qid)}\b', block)]
    if not id_marks:
        return None, {}, None
    start = id_marks[0] + len(f'ID: {qid}')
    am = re.search(rf'ID:\s*{re.escape(qid)}\s*Answer\b', block)
    if not am:
        return None, {}, None
    choices_end = am.start()
    cm = re.search(r'Correct Answer:\s*([A-D])', block[am.end():])
    if not cm:
        return None, {}, None
    correct = cm.group(1)

    letter_m = re.search(r'(?m)^[A-D]\.\s*', block[start:choices_end])
    if not letter_m:
        return None, {}, None
    question_text = norm(block[start:start + letter_m.start()])
    choices_text = block[start + letter_m.start():choices_end]

    parts = re.split(r'(?m)^([A-D])\.\s*', choices_text)
    choices = {}
    for i in range(1, len(parts), 2):
        letter = parts[i]
        text = norm(parts[i + 1]) if i + 1 < len(parts) else ''
        choices[letter] = text

    return question_text, choices, correct

def parse_rationale(qid, block):
    rm = re.search(r'\nRationale\s*\n(.*?)\nQuestion Difficulty:', block, re.DOTALL)
    if not rm:
        return ""
    return norm(rm.group(1))

def main():
    text = extract_text()
    blocks = split_blocks(text)
    print(f"blocks: {len(blocks)}")

    questions = []
    flagged = []
    for qid, block in blocks:
        meta = parse_metadata(block)
        question_text, choices, correct = parse_question_and_choices(qid, block)
        rationale = parse_rationale(qid, block)

        problems = []
        if not meta.get("domain"):
            problems.append(f"domain={meta.get('domain')!r}")
        if not meta.get("skill"):
            problems.append(f"skill={meta.get('skill')!r}")
        if not meta.get("difficulty"):
            problems.append("no difficulty")
        if len(choices) != 4:
            problems.append(f"choices={len(choices)}")
        if not correct:
            problems.append("no correct answer")
        if not question_text:
            problems.append("no question text")
        if not rationale:
            problems.append("no rationale")

        questions.append({
            "id": qid,
            "domain": meta.get("domain"),
            "skill": meta.get("skill"),
            "difficulty": meta.get("difficulty"),
            "question": question_text,
            "choices": choices,
            "correct": correct,
            "rationale": rationale,
        })
        if problems:
            flagged.append((qid, problems))

    print(f"\nparsed {len(questions)} questions, {len(flagged)} flagged")
    for qid, problems in flagged:
        print(" FLAG:", qid, problems)

    with open('/Users/ayaandave/Desktop/sat-rw-practice/questions_raw_new.json', 'w') as f:
        json.dump(questions, f, indent=1, ensure_ascii=False)
    with open('/Users/ayaandave/Desktop/sat-rw-practice/flagged_new.json', 'w') as f:
        json.dump([qid for qid, _ in flagged], f, indent=1)

if __name__ == '__main__':
    main()
