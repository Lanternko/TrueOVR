#!/usr/bin/env bash
# Remote long jobs on the 5090 with an exit-code file, so a check can tell finished / crashed / died / stalled / running (L-082).
#
#   scripts/rjob.sh start  <dir> <name> <timeout> -- <command...>   start in <dir> on the host, detached
#   scripts/rjob.sh status <dir> <name> [stallMin]                   print one STATE line, exit code = state
#   scripts/rjob.sh wait   <dir> <name> [intervalSec] [stallMin]     poll until not RUNNING (run this with run_in_background)
#
# <dir> is on the remote host (e.g. ~/e122); files written there: <name>.pid, <name>.log, <name>.exit, <name>.cmd
# <timeout> is GNU timeout syntax (6h, 90m). Host: $RJOB_HOST, default kojiek@100.97.181.15 (Tailscale).
# Exit codes: 0 RUNNING, 10 DONE, 11 CRASHED, 12 DIED, 13 STALLED, 14 NOJOB, 20 UNREACHABLE.
# Exit code in <name>.exit: 124 = hit timeout, 137 = killed (kill -9 / OOM), anything else non-zero = program error.
set -u
HOST=${RJOB_HOST:-kojiek@100.97.181.15}
SSH=(ssh -o ConnectTimeout=10 -o BatchMode=yes -o ServerAliveInterval=15 "$HOST")

q() { printf '%q' "$1"; }

cmd_start() {
  local dir=$1 name=$2 limit=$3; shift 3
  [ "${1:-}" = "--" ] && shift
  [ $# -gt 0 ] || { echo "start: missing command" >&2; exit 2; }
  local cmd=""; for a in "$@"; do cmd+=" $(q "$a")"; done
  local inner="echo \$\$ > $name.pid; timeout $limit$cmd > $name.log 2>&1; echo \$? > $name.exit"
  timeout 30 "${SSH[@]}" "cd $dir && rm -f $name.exit $name.pid && printf '%s\n' $(q "$cmd") > $name.cmd && { nohup sh -c $(q "$inner") </dev/null >/dev/null 2>&1 & } && sleep 1 && cat $name.pid" </dev/null \
    || { echo "UNREACHABLE"; exit 20; }
  echo "STARTED $name in $dir on $HOST"
}

# Prints "STATE detail" and returns the state's exit code.
cmd_status() {
  local dir=$1 name=$2 stall=${3:-20}
  local out
  out=$(timeout 30 "${SSH[@]}" "cd $dir 2>/dev/null || { echo NOJOB no-dir; exit; }
    if [ -f $name.exit ]; then c=\$(cat $name.exit)
      if [ \"\$c\" = 0 ]; then echo DONE exit=0; else echo CRASHED exit=\$c; fi
    elif [ ! -f $name.pid ]; then echo NOJOB no-pid-file
    elif ! kill -0 \$(cat $name.pid) 2>/dev/null; then echo DIED pid=\$(cat $name.pid) no-exit-file
    else age=\$(( (\$(date +%s) - \$(stat -c %Y $name.log)) / 60 ))
      if [ \$age -ge $stall ]; then echo STALLED log-idle=\${age}min; else echo RUNNING log-age=\${age}min; fi
    fi
    echo \"--- \$(tail -n 3 $name.log 2>/dev/null | tr '\n' ' ' | cut -c1-400)\"" </dev/null) || { echo "UNREACHABLE"; return 20; }
  echo "$out"
  case ${out%% *} in RUNNING) return 0;; DONE) return 10;; CRASHED) return 11;; DIED) return 12;; STALLED) return 13;; *) return 14;; esac
}

cmd_wait() {
  local dir=$1 name=$2 every=${3:-300} stall=${4:-20} fails=0 rc out
  while :; do
    # Only the final state is printed, so the background output stays a few lines.
    out=$(cmd_status "$dir" "$name" "$stall"); rc=$?
    [ $rc -ne 0 ] && echo "$(date +%H:%M) $out"
    if [ $rc -eq 20 ]; then fails=$((fails+1)); [ $fails -ge 3 ] && { echo "UNREACHABLE 3 times in a row"; exit 20; }
    else fails=0; [ $rc -ne 0 ] && exit $rc; fi
    sleep "$every"
  done
}

case ${1:-} in
  start)  shift; [ $# -ge 4 ] || { sed -n 4,6p "$0"; exit 2; }; cmd_start "$@";;
  status) shift; [ $# -ge 2 ] || { sed -n 4,6p "$0"; exit 2; }; cmd_status "$@"; exit $?;;
  wait)   shift; [ $# -ge 2 ] || { sed -n 4,6p "$0"; exit 2; }; cmd_wait "$@";;
  *) sed -n 2,12p "$0"; exit 2;;
esac
