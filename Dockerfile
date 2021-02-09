FROM heartexlabs/label-studio:0.9.0

RUN pip install label-studio==0.9.0.post5

COPY engage-labels /project/engage-labels

WORKDIR /project

CMD ["label-studio", "start", "engage-labels", "--use-gevent"]

# label-studio start engage-labels/ --init \
#     --source gcs --source-path engage-labels --input-format json \
#     --target gcs-completions --target-path engage-labels \
#     --force --log-level DEBUG \
#     --source-params '{"use_blob_urls": false, "prefix": "label-studio/raw", "regex": ".*"}' \
#     --target-params '{"prefix": "label-studio/completions"}'
