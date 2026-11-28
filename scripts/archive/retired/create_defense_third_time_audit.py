from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'src/defense_third_game.js').read_text(encoding='utf-8').replace('simulateDefenseThirdGame','simulateDefenseClockAuditGame')
s=s.replace('return Math.max(1,Math.min(seconds*10,shotClock-1,clock-1));','opt.durationAudit?.({origin,limit,eligibleCount:lo,fullCount:a.length,rawSeconds:seconds*opt.pace,deadlineSeconds:seconds,shotClock:shotClock/10,clock:clock/10});\n    return Math.max(1,Math.min(seconds*10,shotClock-1,clock-1));')
(r/'src/defense_third_clock_audit.js').write_text(s,encoding='utf-8')
