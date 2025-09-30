from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_timestamp, monotonically_increasing_id
from pyspark.sql import Row
import json, os, yaml
from logger import get_logger

logger = get_logger("Transform")

def transform():
    with open("./config.yaml", "r") as f:
        config = yaml.safe_load(f)

    raw_dir = config["storage"]["raw"]
    processed_dir = config["storage"]["processed"]
    logger.info("Initialize processed staging area, if not exists")
    os.makedirs(processed_dir, exist_ok=True)

    spark = SparkSession.builder.appName("BikeWeatherPipeline").config("spark.hadoop.io.native.lib.available", "false").getOrCreate()

    logger.info("Loading raw data...")
    with open(os.path.join(raw_dir, "bike_raw.json"), "r") as f:
        bike_data = json.load(f)

    with open(os.path.join(raw_dir, "weather_raw.json"), "r") as f:
        weather_data = json.load(f)

    # ---- Bike stations ----
    stations = bike_data["network"]["stations"]
    # df_bikes = spark.createDataFrame(stations)
    df_bikes = spark.createDataFrame([Row(**s) for s in stations])

    df_dim_station = df_bikes.select(
        col("id").alias("station_id"),
        col("name").alias("station_name"),
        col("latitude"),
        col("longitude"),
        col("extra.address").alias("address"),
        col("extra.has_ebikes").alias("has_ebikes"),
        col("extra.slots").alias("slots")
    ).dropDuplicates(["station_id"])

    df_fact_bikes = df_bikes.select(
        col("id").alias("station_id"),
        to_timestamp(col("timestamp")).alias("timestamp"),
        col("free_bikes"),
        col("empty_slots"),
        (col("free_bikes") + col("empty_slots")).alias("total_slots"),
        col("extra.ebikes").alias("ebikes")
    )

    # ---- Weather ----
    hourly = weather_data["hourly"]
    df_weather = spark.createDataFrame(
        zip(
            hourly["time"],
            hourly["temperature_2m"],
            hourly["precipitation"],
            hourly["wind_speed_10m"],
            hourly["cloudcover"],
            hourly["relativehumidity_2m"]
        ),
        schema=["time", "temperature", "precipitation", "wind_speed", "cloud_cover", "humidity"]
    ).withColumn("timestamp", to_timestamp("time"))

    df_dim_weather = df_weather.withColumn("weather_id", monotonically_increasing_id())

    # Join fact_bikes with weather by timestamp
    df_fact = df_fact_bikes.join(
        df_dim_weather,
        on="timestamp",
        how="left"
    ).select(
        "station_id", "timestamp", "free_bikes", "empty_slots", "total_slots", "ebikes", "weather_id"
    )

    # Save transformed data → processed area (Parquet instead of JSON)
    df_dim_station.write.mode("overwrite").parquet(os.path.join(processed_dir, "dim_station"))
    df_dim_weather.write.mode("overwrite").parquet(os.path.join(processed_dir, "dim_weather"))
    df_fact.write.mode("overwrite").parquet(os.path.join(processed_dir, "fact_bike_weather"))


    logger.info("Stage 2 Transform complete. Data stored in processed area.")

if __name__ == "__main__":
    transform()
