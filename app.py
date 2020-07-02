import streamlit as st
import pandas as pd
import numpy as np
import pandas_gbq
import copy
import uuid

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
    "hashtags"
]

#app functions
@st.cache(allow_output_mutation=True)
def get_unlabelled_comments(comment_limit):
    with st.spinner("Getting unlabelled comments..."):
        query = f"""
            with comments as (
                select
                    _id as comment_id
                    , created_at
                    , concat('instagram_', split(_id, '_')[OFFSET(1)]) as post_id
                    , text
                    , labels
                from `atlas_engage_engage.comments`
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
            order by rand()
            limit {comment_limit}
        """
        df = pd.read_gbq(query, project_id="buffer-data")
        df.set_index("comment_id", drop=True, inplace=True)
        for label in LABELS:
            df[label] = False
        return df

def get_admin_data():
    query = "select * from buffer_engage.comment_labels"
    return pd.read_gbq(query, project_id="buffer-data")

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

st.title("Engage Comment Labeller")

#instructional video
if st.button("View Instructional Video"):
    st.markdown("""
    <div style="position: relative; padding-bottom: 62.5%; height: 0;"><iframe src="https://www.loom.com/embed/635d25e54c824d4397dbb3244b19724a" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"></iframe></div>
    """, unsafe_allow_html=True)

labeller_name = st.text_input("Labeller Name:")
if labeller_name == 'admin':
    admin_df = get_admin_data()
    comments_labelled = admin_df['comment_id'].nunique()
    labellers =  admin_df['labeller'].nunique()

    st.text(f'Total # of comments labelled: {comments_labelled}')
    st.text(f'Total # of labellers: {labellers}')
    "## Raw data"
    admin_df

elif len(labeller_name) > 0:

    #Load comments and make the sidebar
    comment_limit = st.sidebar.slider("Number of comments to load", 1, 50, 20)
    comments_df = get_unlabelled_comments(comment_limit)

    if st.sidebar.button("Save Labels"):
        save_labels(comments_df)
        st.caching.clear_cache()
        comments_df = get_unlabelled_comments(comment_limit)

    if st.sidebar.button("Reload"):
        st.caching.clear_cache()
        comments_df = get_unlabelled_comments(comment_limit)

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

