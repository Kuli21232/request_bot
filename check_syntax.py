import ast, sys
files = [
    'bot/services/ai_classifier.py',
    'bot/services/topic_ai_engine.py',
    'bot/services/topic_automation_service.py',
    'bot/services/topic_learning_service.py',
    'bot/services/signal_threader.py',
]
ok = True
for path in files:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            src = f.read()
        ast.parse(src)
        sys.stdout.write(f'OK  {path}\n')
    except SyntaxError as e:
        sys.stdout.write(f'ERR {path}: {e}\n')
        ok = False
sys.stdout.flush()
sys.exit(0 if ok else 1)
