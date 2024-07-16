import datetime
import os
import pickle

import pandas as pd
import pendulum
from airflow.decorators import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.postgres.operators.postgres import PostgresOperator
from geotext import GeoText
from tweety import Twitter, filters


@dag(
    dag_id="process_tweets",
    # Cron expression to execute the DAG every minute '* * * * *' (5 minutes '*/5 * * * *')
    schedule_interval="*/5 * * * *",
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    # This is set to False to prevent backfilling, that is running the DAG for the time period that was missed
    catchup=False,
    # This is the time limit for the DAG to run
    dagrun_timeout=datetime.timedelta(minutes=60),
)
def ProcessTweets():
    create_tweets_table = PostgresOperator(
        task_id="create_tweets_table",
        postgres_conn_id="postgres_conn_tfm",
        sql="""
            CREATE TABLE IF NOT EXISTS tweets (
                "ID" NUMERIC PRIMARY KEY,
                "DATE" TIMESTAMP WITH TIME ZONE,
                "TEXT" TEXT,
                "URL" TEXT,
                "LABEL" TEXT,
                "LOCATION" TEXT
            );""",
    )

    @task
    def extract_tweets(**context):
        app = Twitter("session")

        username = os.environ.get("twitter_username")
        password = os.environ.get("twitter_password")

        app.sign_in(username=username, password=password)

        dags_path = "/opt/airflow/dags"

        if os.path.exists(f"{dags_path}/cursor_top.txt"):
            with open(f"{dags_path}/cursor_top.txt", "r") as file:
                cursor_top = file.read()
        else:
            cursor_top = None

        all_tweets = app.search(
            keyword="@policiaecuador -from:@policiaecuador lang:es",
            filter_=filters.SearchFilters.Latest(),
            pages=1,
            wait_time=5,
            cursor=cursor_top,
        )

        if all_tweets:
            # Save cursor
            with open(f"{dags_path}/cursor_top.txt", "w") as f:
                f.write(all_tweets.cursor_top)

            id, date, text, url, location = [], [], [], [], []

            for tweet in all_tweets:
                cities = GeoText(tweet.text).cities
                if cities:
                    location.append(cities)
                else:
                    place = tweet.place
                    if place is not None:
                        location.append([place.name])
                    else:
                        location.append([])

                id.append(int(tweet.id))
                date.append(tweet.date)
                text.append(str(tweet.text).replace("\n", " "))
                url.append(tweet.url)

            data = pd.DataFrame(
                data={
                    "id": id,
                    "date": date,
                    "text": text,
                    "url": url,
                    "location": location,
                }
            )

            data.location = data.location.str.join(",")

            context["ti"].xcom_push(key="data", value=data)

    @task
    def transform_tweets(**context):
        dags_path = "/opt/airflow/dags"
        data = context["ti"].xcom_pull(key="data")

        if data is not None:
            with open(f"{dags_path}/model_decision_tree.pkl", "rb") as f:
                model_loaded = pickle.load(f)

            prediction = model_loaded.predict(data["text"])
            data["label"] = prediction

            context["ti"].xcom_push(key="data", value=data)

    @task
    def load_tweets(**context):
        data = context["ti"].xcom_pull(key="data")

        if data is not None:
            postgres_hook = PostgresHook(postgres_conn_id="postgres_conn_tfm")
            conn = postgres_hook.get_conn()
            cursor = conn.cursor()
            for _, row in data.iterrows():
                cursor.execute(
                    f"""
                    INSERT INTO tweets ("ID", "DATE", "TEXT", "URL", "LABEL", "LOCATION")
                    VALUES ({row['id']}, '{row['date']}', $$'{row['text']}'$$, '{row['url']}', '{row['label']}', '{row['location']}')
                    ON CONFLICT DO NOTHING;
                    """
                )
            conn.commit()
            cursor.close()
            conn.close()

    create_tweets_table >> extract_tweets() >> transform_tweets() >> load_tweets()


dag = ProcessTweets()
