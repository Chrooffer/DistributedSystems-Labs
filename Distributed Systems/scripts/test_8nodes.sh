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

for i in `seq 100 119`; do #20 posts from node 6
	curl -d 'entry=t'${i} -X 'POST' 'http://10.1.0.6/board' &
done

for i in `seq 120 139`; do #20 posts from node 7
	curl -d 'entry=t'${i} -X 'POST' 'http://10.1.0.7/board' &
done

for i in `seq 140 159`; do #20 posts from node 8
	curl -d 'entry=t'${i} -X 'POST' 'http://10.1.0.8/board' &
done

