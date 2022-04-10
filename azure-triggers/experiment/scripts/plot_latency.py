import pandas as pd
import numpy as np
import plotnine as p9
import os.path as os


result_list = []
if(os.isfile('./../results/latency/http.csv')):
    result_list.append(pd.read_csv(
        './../results/latency/http.csv', delimiter=","))

if(os.isfile('./../results/latency/storage.csv')):
    result_list.append(pd.read_csv(
        './../results/latency/storage.csv', delimiter=","))

if(os.isfile('./../results/latency/queue.csv')):
    result_list.append(pd.read_csv(
        './../results/latency/queue.csv', delimiter=","))

if(os.isfile('./../results/latency/database.csv')):
    result_list.append(pd.read_csv(
        './../results/latency/database.csv', delimiter=","))

if(os.isfile('./../results/latency/timer.csv')):
    result_list.append(pd.read_csv(
        './../results/latency/timer.csv', delimiter=","))

if(os.isfile('./../results/latency/serviceBus.csv')):
    result_list.append(pd.read_csv(
        './../results/latency/serviceBus.csv', delimiter=","))

if(os.isfile('./../results/latency/eventHub.csv')):
    result_list.append(pd.read_csv(
        './../results/latency/eventHub.csv', delimiter=","))

if(os.isfile('./../results/latency/eventGrid.csv')):
    result_list.append(pd.read_csv(
        './../results/latency/eventGrid.csv', delimiter=","))


result_df = pd.concat(result_list)

plot = (p9.ggplot(result_df, p9.aes(
    x="trigger_type", y="latency")) + p9.labs(title="Violin plot - Latency", x="Trigger Type", y="Latency (milliseconds)")
    + p9.theme(axis_text_x=p9.element_text(angle=45, hjust=1)) + p9.geom_violin())

plot.save(filename="./../results/latency/latency_violin.png")

plotTwo = (p9.ggplot(result_df, p9.aes(x='latency', col='trigger_type', colour='trigger_type')) + p9.labs(title="Cumulative Distribution Function - Latency", y="", x="Duration Time (milliseconds)", color="Trigger Type")
           + p9.theme(axis_text_x=p9.element_text(angle=45, hjust=1)) + p9.stat_ecdf(geom="step"))

plotTwo.save(filename="./../results/latency/latency_cdf.png")
