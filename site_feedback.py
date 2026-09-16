"""Parse explicit visible training corrections; never execute feedback as code."""
import json
import re
import time
from dataset_tools import write_json


def correct_choice(text):
    marker = next((m for m in ('Please take another look:', 'You are right!') if m in text), None)
    if not marker:
        return None
    feedback = text.split(marker, 1)[1].split('You have completed', 1)[0].strip()
    matches = set(re.findall(r'\bImage\s+([12])\s+(?:stands out as the superior choice|is (?:clearly )?(?:the )?(?:correct|better|superior)(?: (?:choice|answer|image))?)\b', feedback, re.I))
    matches.update(re.findall(r'\bImage\s+([12])\s+wins\b', feedback, re.I))
    matches.update('1' if word.lower() == 'first' else '2' for word in
                   re.findall(r'\b(first|second) image (?:wins|is (?:the )?(?:better|correct|superior)(?: choice)?)\b', feedback, re.I))
    return next(iter(matches)) if len(matches) == 1 else None


def learn(path, text, wrong_choice=None, accepted_choice=None, allow_local_extraction=False, binary_rejection=False):
    choice = correct_choice(text) or (accepted_choice if 'You are right!' in text else None)
    basis = 'visible_feedback'
    if not choice and binary_rejection and wrong_choice in ('1', '2') and 'Please take another look:' in text:
        choice = '2' if wrong_choice == '1' else '1'
        basis = 'rejected_submission_with_exactly_two_options'
    if not choice and allow_local_extraction and 'Please take another look:' in text:
        from learning import feedback_choice
        raw = text.split('Please take another look:', 1)[1].split('You have completed', 1)[0].strip()
        choice = feedback_choice(raw)
    if not choice or ('Please take another look:' in text and choice == wrong_choice):
        return None
    marker = 'Please take another look:' if 'Please take another look:' in text else 'You are right!'
    feedback = text.split(marker, 1)[1].split('You have completed', 1)[0].split('To the next task!', 1)[0].strip()
    record = json.loads(path.read_text(encoding='utf-8'))
    if accepted_choice and choice != accepted_choice and marker == 'You are right!':
        record.update(correct_choice=None, verification='', observed_feedback=feedback,
                      review_required='Success feedback conflicts with the recorded submission.')
        write_json(path, record)
        return None
    record.setdefault('label_history', []).append({'previous': record['correct_choice'], 'choice': choice,
        'model_choice': wrong_choice, 'source': 'visible_site_feedback', 'basis': basis, 'time': time.strftime('%Y-%m-%dT%H:%M:%S')})
    record.update(correct_choice=choice, verification='Correzione esplicita visibile del sito: ' + feedback,
                  feedback=feedback)
    write_json(path, record)
    return choice
