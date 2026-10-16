"""Retry model requests only. Tool execution is never retried here."""
import time
from importlib.metadata import version
from dotenv import dotenv_values


def settings():
    import os
    values = {**dotenv_values('.env'), **os.environ}
    return {
        'model': values.get('GEMINI_MODEL', 'gemini-3.5-flash-lite'),
        'timeout_ms': max(1000, min(120000, int(values.get('GEMINI_TIMEOUT_MS', '30000')))),
        'attempts': max(1, min(3, int(values.get('GEMINI_ATTEMPTS', '2')))),
        'max_steps': max(1, min(12, int(values.get('AGENT_MAX_STEPS', '8')))),
    }


def generate(client, config, messages, workspace, options):
    for attempt in range(1, options['attempts'] + 1):
        if sum(r.get('duration_seconds', 0) for r in workspace.requests) >= 180:
            raise TimeoutError('Model request time budget reached; existing tool actions are retained in the audit.')
        started = time.monotonic()
        workspace.notify(f"Model request {len(workspace.requests)+1} · attempt {attempt}/{options['attempts']}")
        entry = {'attempt': attempt, 'model': options['model']}
        try:
            response = client.models.generate_content(model=options['model'], contents=messages, config=config)
            entry['status'] = 'ok'
            usage = getattr(response, 'usage_metadata', None)
            if usage is not None and hasattr(usage, 'model_dump'):
                entry['usage'] = usage.model_dump(mode='json', exclude_none=True)
            return response
        except Exception as exc:
            code = getattr(exc, 'code', None)
            entry.update(status='error', code=code, error_type=type(exc).__name__)
            if code not in (429, 500, 502, 503, 504) or attempt == options['attempts']:
                raise
            workspace.notify(f"Provider returned {code}; retrying this request in {2**attempt} seconds")
            time.sleep(2**attempt)
        finally:
            entry['duration_seconds'] = round(time.monotonic()-started, 3)
            workspace.requests.append(entry)


def metadata(options):
    return {**options, 'provider': 'gemini', 'sdk_version': version('google-genai')}
