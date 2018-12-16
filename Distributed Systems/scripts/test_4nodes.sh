#! /bin/bash
echo "test for labs"
for i in `seq 0 20`; do #5 posts from each node
	curl -d 'entry=t'${i} -X 'POST' 'http://10.1.0.'$(((i%4)+1))'/board'
done
