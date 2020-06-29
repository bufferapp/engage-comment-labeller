import streamlit as st
import pandas as pd
import numpy as np
import pandas_gbq
import copy

@st.cache
def get_unlabelled_comments(comment_limit):
    with st.spinner('Getting unlabelled comments...'):
        query = f"""
            with comments as (
            select
                _id as id
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
            from `atlas_engage_engage.posts`
            )
            select
                p.*
                , c.* except (post_id)
            from comments c
                inner join posts p on p.post_id = c.post_id
            where c.labels != '[]'
            order by rand()
            limit {comment_limit}
        """
        df = pd.read_gbq(query, project_id='buffer-data')
        df.set_index('id', drop=True, inplace=True)
        for label in ['is_negative', 'is_question', 'is_order', 'is_toxic', 'dont_know']:
            df[label] = False
        return df

def save_labels(df):
    pandas_gbq.to_gbq(df
        , 'buffer_engage.comment_labels'
        , project_id='buffer-data'
        , if_exists='append')
    st.caching.clear_cache()

def set_label(label, id, value):
    comments_df.loc[id][label] = value

comment_limit = st.sidebar.slider('Number of comments to load', 1, 50, 20)

if st.sidebar.button('Reload'):
    st.caching.clear_cache()

comments_df = copy.deepcopy(get_unlabelled_comments(comment_limit))

st.title('Engage Comment Labeller')

if st.sidebar.button('Save Labels'):
    save_labels(comments_df)


for comment_id, comment in comments_df.iterrows():
    st.markdown("## Post")
    st.markdown(f"[Link]({comment['post_permalink']})")
    st.image(comment['post_media_url'], width=640)
    st.markdown(f"**Caption** {comment['post_caption']}")

    st.markdown('## Comment')
    st.markdown(comment['text'])

    st.markdown('## Labels')
    negative = st.checkbox("NEGATIVE", key=f"neg-{comment_id}")
    set_label('is_negative', comment_id, negative)

    question = st.checkbox("QUESTION", key=f"question-{comment_id}")
    set_label('is_question', comment_id, question)


    order = st.checkbox("ORDER", key=f"ord-{comment_id}")
    set_label('is_order', comment_id, question)

    toxic = st.checkbox("TOXIC", key=f"toxic-{comment_id}")
    set_label('is_toxic', comment_id, toxic)

    dont_know = st.checkbox("DON'T KNOW", key=f"dont-know-{comment_id}")
    set_label('dont_know', comment_id, toxic)

    st.markdown('---')