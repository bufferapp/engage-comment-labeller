import streamlit as st
import pandas as pd
import numpy as np
import pandas_gbq
import copy
import uuid
from dataclasses import dataclass
from google.cloud import language
from google.cloud.language import types, enums
from sklearn import metrics

LABELS = [
    "none",
    "dont_know",
    "positive",
    "praise",
    "negative",
    "question",
    "order",
    "toxic",
    "spam",
    "private",
    "mentions",
    "hashtags",
    "giveaway"
]

#app functions
@st.cache(allow_output_mutation=True)
def get_unlabelled_comments(comment_limit, labeller_name, sample_from):
    with st.spinner("Getting unlabelled comments..."):
        if sample_from == 'negative':
            sample_from_clause = "comment_id in (select id from `buffer_engage.potentially_negative_comments`)"
        else:
            sample_from_clause = 'true'

        query = f"""
            with comments as (
                select
                    _id as comment_id
                    , created_at
                    , concat('instagram_', split(_id, '_')[OFFSET(1)]) as post_id
                    , text
                    , labels
                from `atlas_engage_engage.comments`
                where {sample_from_clause}
            )
            , posts as (
                select
                    _id as post_id
                    , json_extract_scalar(media, '$.caption') as post_caption
                    , json_extract_scalar(media, '$.mediaUrl') as post_media_url
                    , json_extract_scalar(media, '$.permalink') as post_permalink
                    , json_extract_scalar(media, '$.shortcode') as media_shortcode
                    , json_extract_scalar(media, '$.type') as type
                from `atlas_engage_engage.posts`
            )
            select
                p.*
                , c.* except (post_id)
            from comments c
                inner join posts p on p.post_id = c.post_id
            where p.type = 'IMAGE' -- we only support image posts for now
                and comment_id not in (
                    select comment_id from buffer_engage.comment_labels where labeller != '{labeller_name}'
                )
            order by rand()
            limit {comment_limit}
        """
        df = pd.read_gbq(query, project_id="buffer-data")
        df.set_index("comment_id", drop=True, inplace=True)
        for label in LABELS:
            df[label] = False
        return df

def save_labels(df):
    if len(labeller_name) == 0:
        st.error("Please select the Labeller Name!")
        return
    else:
        df["labeller"] = labeller_name
    df["labelled_at"] = pd.Timestamp.now()
    df.reset_index(inplace=True) # so we store the comment_id
    df['id'] = df.comment_id.map(lambda i: uuid.uuid4())

    pandas_gbq.to_gbq(
        df, "buffer_engage.comment_labels", project_id="buffer-data", if_exists="append"
    )

def set_label(df, label, id, value):
    df.loc[id, label] = value

#admin functions
nl_client = language.LanguageServiceClient()

@dataclass
class CommentLabelsData:
    raw_df: pd.DataFrame
    labellers_df: pd.DataFrame
    comments_labelled: int
    labellers: int

@dataclass
class NegativityStatsData:
    df: pd.DataFrame
    stats: pd.DataFrame


st.cache(show_spinner=False)
def predict_negative(text):
    from google.api_core.exceptions import InvalidArgument
    try:
        document = types.Document(
            content=text,
            type=enums.Document.Type.PLAIN_TEXT)
        sentiment = nl_client.analyze_sentiment(document=document).document_sentiment
        return sentiment
    except InvalidArgument as e:
        return language.types.Sentiment()


@st.cache(allow_output_mutation=True)
def get_comment_labels_data():
    query = "select * from buffer_engage.comment_labels"
    df = pd.read_gbq(query, project_id="buffer-data")
    comments_labelled = df['comment_id'].nunique()
    labellers =  df['labeller'].nunique()
    labellers_df = df.groupby(['labeller']).size().reset_index(name='counts')

    return CommentLabelsData(df, labellers_df, comments_labelled, labellers)

@st.cache
def calculate_negativity_stats(df, threshold=-0.7):
    output_df = copy.deepcopy(df)
    predictions = output_df['text'].map(predict_negative)

    output_df['sentiment_score'] = predictions.map(lambda p: p.score)
    output_df['negative_prediction'] = output_df['sentiment_score'].map(lambda s: s < threshold)

    n_actual = len(output_df[output_df['negative']])
    n_predicted = len(output_df[output_df['negative_prediction']])
    precision = metrics.precision_score(output_df['negative'], output_df['negative_prediction'])
    recall = metrics.recall_score(output_df['negative'], output_df['negative_prediction'])
    f1_score = metrics.f1_score(output_df['negative'], output_df['negative_prediction'])

    output_df = output_df[['id', 'text', 'negative', 'sentiment_score', 'negative_prediction']]

    stats = pd.DataFrame({'actual': [n_actual],
        'predicted': [n_predicted],
        'precision': [precision],
        'recall': [recall],
        'f1_score': [f1_score]})

    return NegativityStatsData(output_df, stats)

st.title("Engage Comment Labeller")

#instructional video
if st.button("View Instructional Video"):
    st.markdown("""
    <div style="position: relative; padding-bottom: 62.5%; height: 0;"><iframe src="https://www.loom.com/embed/635d25e54c824d4397dbb3244b19724a" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"></iframe></div>
    """, unsafe_allow_html=True)

labeller_name = st.text_input("Labeller Name:")
if labeller_name == 'admin':
    comment_labels_data = get_comment_labels_data()

    st.text(f'Total # of comments labelled: {comment_labels_data.comments_labelled}')
    st.text(f'Total # of labellers: {comment_labels_data.labellers}')
    "## Labeller stats"
    comment_labels_data.labellers_df

    "## Raw data"
    comment_labels_data.raw_df

    "## Label Breakdown"
    breakdown = (comment_labels_data.raw_df[LABELS] == True).sum()
    breakdown
    # if st.button('Calculate Negativity Stats'):
    #     "### Negativity Stats"
    #     stats = calculate_negativity_stats(comment_labels_data.raw_df)
    #     stats.df
    #     stats.stats
    # "*This takes a while to run if not cached!*"

elif len(labeller_name) > 0:

    sample_from = st.sidebar.selectbox(
        "Which data should be sample?",
        ('all', 'negative'),
        format_func=lambda o: 'All' if o == 'all' else 'Potentially Negative'
    )

    #Load comments and make the sidebar
    comment_limit = st.sidebar.slider("Number of comments to load", 1, 50, 20)
    comments_df = get_unlabelled_comments(comment_limit, labeller_name, sample_from)

    if st.sidebar.button("Save Labels"):
        save_labels(comments_df)
        st.caching.clear_cache()
        comments_df = get_unlabelled_comments(comment_limit, labeller_name, sample_from)

    if st.sidebar.button("Reload"):
        st.caching.clear_cache()
        comments_df = get_unlabelled_comments(comment_limit, labeller_name, sample_from)



    # Load sample commments
    for comment_id, comment in comments_df.iterrows():
        st.markdown("## Post")
        st.markdown(f"[Link]({comment['post_permalink']})")
        st.image(comment["post_media_url"], width=640)
        st.markdown(f"**Caption** {comment['post_caption']}")

        st.markdown("## Comment")
        st.markdown(comment["text"])

        st.markdown("## Labels")

        for label in LABELS:
            value = st.checkbox(
                label.upper().replace("_", " "), key=f"{label}-{comment_id}"
            )
            set_label(comments_df, label, comment_id, value)

        st.markdown("---")

