"""Saved live-comparison viewer; never makes model calls."""
import csv
import io
import json
import streamlit as st


def load_comparisons(root):
    rows, errors = [], []
    for path in sorted((root / 'logs').glob('comparison_*.json')):
        try:
            comparison = json.loads(path.read_text(encoding='utf-8-sig'))
            runs = comparison['runs']
            if not isinstance(runs, list) or not runs:
                raise ValueError('No run records')
            file_rows = []
            for run in runs:
                audit = run['audit']
                file_rows.append({
                    'Recorded (UTC)': comparison['started_at'],
                    'Document': comparison['document'],
                    'Task': comparison['task'],
                    'Mode': run['mode'],
                    'Status': run['status'],
                    'Unauthorized executed': run['unauthorized_actions_executed'],
                    'Blocked calls': sum(e['decision'] == 'BLOCK' for e in audit),
                    'Simulated emails': len(run['outbox']),
                    'Marker in answer': run['secret_marker_in_answer'],
                    'Marker sent to attacker': run['secret_marker_sent_to_attacker'],
                    'Utility review': 'Not automatically scored',
                    'Log file': path.name,
                })
            rows.extend(file_rows)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f'{path.name}: {type(exc).__name__}')
    return rows, errors


def render_saved_results(root):
    st.subheader('Saved live evaluations')
    st.caption('Loaded from local comparison logs. Completed means the agent returned an answer; task correctness requires review. Repeated runs are retained.')
    st.button('Refresh saved results')
    rows, errors = load_comparisons(root)
    if errors:
        st.warning(f'{len(errors)} comparison files could not be loaded.')
        with st.expander('Files requiring attention'):
            st.write(errors)
    if not rows:
        st.info('No saved live comparisons yet. Run both modes below to create one.')
        return
    a, b, c = st.columns(3)
    a.metric('Recorded runs', len(rows))
    b.metric('Completed runs', sum(r['Status'] == 'completed' for r in rows))
    c.metric('Error / incomplete runs', sum(r['Status'] != 'completed' for r in rows))
    mode = st.selectbox('Show mode', ['Both', 'Gate ON', 'Gate OFF'])
    filtered = [r for r in rows if mode == 'Both' or r['Mode'] == mode]
    st.dataframe(filtered, use_container_width=True, hide_index=True)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    for row in filtered:
        # Prevent spreadsheet formula interpretation of user task text.
        writer.writerow({k: "'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v for k, v in row.items()})
    st.download_button('Download evaluation CSV', output.getvalue(), 'live-evaluation.csv', 'text/csv')
    st.caption('Zero unauthorized actions with both modes does not establish added protection from the gate. Scripted gate checks must be reported separately.')
