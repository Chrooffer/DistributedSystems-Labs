#! /bin/bash
echo "test for labs"
for i in `seq 0 19`; do #20 posts from node 1
	curl -d 'entry=t'${i} -X 'POST' 'http://10.1.0.1/board' &
done

for i in `seq 20 39`; do #20 posts from node 2
	curl -d 'entry=t'${i} -X 'POST' 'http://10.1.0.2/board' &
done

for i in `seq 40 59`; do #20 posts from node 3
	curl -d 'entry=t'${i} -X 'POST' 'http://10.1.0.3/board' &
done

for i in `seq 60 79`; do #20 posts from node 4
	curl -d 'entry=t'${i} -X 'POST' 'http://10.1.0.4/board' &
done

for i in `seq 80 99`; do #20 posts from node 5
	curl -d 'entry=t'${i} -X 'POST' 'http://10.1.0.5/board' &
done
