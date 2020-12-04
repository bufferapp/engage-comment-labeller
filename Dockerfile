FROM heartexlabs/label-studio:latest

COPY engage-labels /project/engage-labels

WORKDIR /project

CMD ["label-studio", "start", "engage-labels", "--use-gevent"]
