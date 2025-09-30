import os

import psycopg2
import yaml
from pyspark.sql import SparkSession

from logger import get_logger

logger = get_logger("Load")


def load():
    with open("../config.yaml", "r") as f:
        config = yaml.safe_load(f)

    db_conf = config["database"]
    processed_dir = config["storage"]["processed"]

    spark = SparkSession.builder.appName("BikeWeatherPipeline").getOrCreate()

    # Load processed parquet
    df_dim_station = spark.read.parquet(os.path.join(processed_dir, "dim_station.parquet"))
    df_dim_weather = spark.read.parquet(os.path.join(processed_dir, "dim_weather.parquet"))
    df_fact = spark.read.parquet(os.path.join(processed_dir, "fact_bike_weather.parquet"))

    # Collect to Pandas for psycopg2 insertion
    pdf_station = df_dim_station.toPandas()
    pdf_weather = df_dim_weather.toPandas()
    pdf_fact = df_fact.toPandas()

    conn = psycopg2.connect(
        dbname=db_conf["dbname"],
        user=db_conf["user"],
        password=db_conf["password"],
        host=db_conf["host"],
        port=db_conf["port"]
    )
    cur = conn.cursor()

    logger.info("Inserting dimension: station...")
    for _, row in pdf_station.iterrows():
        cur.execute("""
            INSERT INTO dim_station (station_id, station_name, latitude, longitude, address, has_ebikes, slots)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (station_id) DO NOTHING;
        """, (
            row["station_id"], row["station_name"], row["latitude"], row["longitude"],
            row["address"], row["has_ebikes"], row["slots"]
        ))

    logger.info("Inserting dimension: weather...")
    for _, row in pdf_weather.iterrows():
        cur.execute("""
            INSERT INTO dim_weather (timestamp, temperature, precipitation, wind_speed, cloud_cover, humidity)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING weather_id;
        """, (
            row["timestamp"], row["temperature"], row["precipitation"], row["wind_speed"],
            row["cloud_cover"], row["humidity"]
        ))

    logger.info("Inserting fact table...")
    for _, row in pdf_fact.iterrows():
        cur.execute("""
            INSERT INTO fact_bike_weather (station_id, weather_id, timestamp, free_bikes, empty_slots, total_slots, ebikes)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (
            row["station_id"], row["weather_id"], row["timestamp"],
            row["free_bikes"], row["empty_slots"], row["total_slots"], row["ebikes"]
        ))

    conn.commit()
    cur.close()
    conn.close()
    logger.info("Stage 3 Load complete. Data written to Postgres.")


if __name__ == "__main__":
    load()
