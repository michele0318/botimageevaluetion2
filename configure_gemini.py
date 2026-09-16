"""Configure locally; never pass an API key on the command line."""
import argparse
import getpass
import json
import math
import run_task_bot as bot
import gemini_provider as gemini


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local', action='store_true')
    args = parser.parse_args()
    settings = {'provider': 'ollama'}
    if not args.local:
        print('Gemini invia prompt e immagini a Google. La quota API e separata dall’app Gemini.')
        print('Modello:', gemini.DEFAULT_MODEL)
        cap = float(input('Limite giornaliero stimato in USD per questo bot [1]: ').strip() or '1')
        if not math.isfinite(cap) or cap <= 0:
            parser.error('Inserire un importo positivo e finito.')
        secret = getpass.getpass('Chiave Google AI Studio (nascosta): ').strip()
        if not secret:
            parser.error('Chiave mancante. Configurazione invariata.')
        bot.STATE.mkdir(parents=True, exist_ok=True)
        (bot.STATE / 'gemini-key.bin').write_bytes(bot.protect_session(secret.encode()))
        settings = {'provider': 'gemini', 'model': gemini.DEFAULT_MODEL, 'daily_usd': cap}
    bot.STATE.mkdir(parents=True, exist_ok=True)
    temporary = bot.STATE / 'ai-provider.tmp'
    temporary.write_text(json.dumps(settings, indent=2), encoding='utf-8')
    temporary.replace(bot.STATE / 'ai-provider.json')
    print('Provider salvato:', settings['provider'], '. Nessuna richiesta API eseguita.')


if __name__ == '__main__':
    main()
