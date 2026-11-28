from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'scripts/defense_scoreboard_uncertainty.js').read_text(encoding='utf-8')
s=s.replace("const root='reports/defense-b1'","const root='reports/defense-third'")
s=s.replace('scripts/defense_scoreboard_uncertainty.js','scripts/defense_third_uncertainty.js')
(r/'scripts/defense_third_uncertainty.js').write_text(s,encoding='utf-8')
