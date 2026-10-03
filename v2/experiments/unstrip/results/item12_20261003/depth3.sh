#!/bin/bash
# §8.7 item 12, part B: four declaration depths, six sandboxes each, three interleaved rounds.
cd ~/r2exp/v2/experiments/unstrip
P=~/r2exp/ha314/bin/python
D=~/r2exp/t2/platform-deps-aug
O=~/r2exp/t2/item12_20261003
for round in c3; do
  for point in none two four ten; do
    case $point in
      none) a="--profile minimal" ;;
      two)  a="--components http,websocket_api" ;;
      four) a="--components frontend,http,websocket_api,lovelace" ;;
      ten)  a="--profile unstripped" ;;
    esac
    echo "== round $round $point"
    systemd-run --user --scope -q python3 scale.py --count 3 --python $P $a \
      --platform-deps $D --json $O/depth_${point}_r${round}.json 2>&1 | grep -E "PSS per|sandbox [0-9]|never|Error|error" 
    sleep 20
  done
done
echo ALLDONE
