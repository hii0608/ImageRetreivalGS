from cbir_subsg.test import validation
from utils import utils
from utils import data
from cbir_subsg import models
from cbir_subsg.conf import parse_encoder

import torch.optim as optim
import torch.nn as nn
import torch
import os, sys
import argparse

import time
import pickle, random, tqdm
import networkx as nx
from deepsnap.graph import Graph as DSGraph
from deepsnap.batch import Batch
import numpy as np


def build_model(args):
    if args.method_type == "gnn":
        model = models.GnnEmbedder(args.feature_dim, args.hidden_dim, args)  # feature vector("rpe")가 num_walks = 4라 5차원
    model.to(utils.get_device())

    # checkpoint = torch.load('checkpoint.pt')

    if os.path.exists(args.model_path):
        model.load_state_dict(torch.load(args.model_path,
                                         map_location=utils.get_device()))
    return model

def batch_nx_graphs_rpe(graphs, anchors=None):
    newGraphs = []
    if anchors is not None:
        for anchor, g in zip(anchors, graphs):
            for v in g.nodes:
                g.nodes[v]["node_feature"] = torch.tensor([float(v == anchor)])
                print("g.nodes[v] : ",  g.nodes[v])
            
            for e in g.edges:
                g.edges[e]["edge_feature"] = torch.tensor([float(v == anchor)])
                print("g.edges[v] : ",  g.edges[v])

    for g in graphs:
        newG = nx.Graph()
        newG.add_nodes_from(g.nodes(data=True))
        newG.add_edges_from(g.edges())

        for v in list(g.nodes):
                rpe = g.nodes[v]['rpe']
                f0 = g.nodes[v]["txtemb"]
                newG.nodes[v]["node_feature"] = torch.tensor(np.concatenate((rpe, f0), axis=None))

        for e in list(g.edges):
                txtemb = g.edges[e[0], e[1]]['txtemb'] # 10 
                distance = g.edges[e[0], e[1]]["distance"] #1
                angle_AB = g.edges[e[0], e[1]]["angle_AB"] # 1
                angle_BA = g.edges[e[0], e[1]]["angle_BA"] #1 
                # newG.edges[e]["edge_feature"] = torch.tensor(np.concatenate((txtemb, distance,angle_AB,angle_BA), axis=None))
                newG.edges[e]["edge_feature"] = torch.tensor(np.concatenate((distance, angle_AB), axis=None), dtype=torch.float32)
                
        newGraphs.append(newG)
        # print("newGraphs: ",newGraphs)
    batch = Batch.from_data_list([DSGraph(g) for g in newGraphs])  
    
    # print("batch: ",batch)

    try:
        batch = batch.to(utils.get_device())
    except:
        print(graphs)
    # print(batch)
    return batch



class DataSource:
    def gen_batch(batch_target, batch_neg_target, batch_neg_query, train):
        raise NotImplementedError


# def data_generator(data_folder, batch_size):
#     dataset = [[], [], []]

#     # 전체 파일 목록을 가져옵니다.
#     all_files = []
#     for foldername in os.listdir(data_folder):
#         file_names = os.listdir(os.path.join(data_folder, foldername))
#         all_files.extend([os.path.join(data_folder, foldername, filename) for filename in file_names])

#     # 파일 목록을 셔플하거나 다른 방식으로 조정할 수 있습니다.
#     random.shuffle(all_files)
#     print("len(all_files): ",len(all_files))
    
#     # all_files = all_files[:3]
#     # while True:
#     start = time.time()
#     for file_path in all_files:
#         with open(file_path, "rb") as fr:
#             tmp = pickle.load(fr)
#             for i in range(len(tmp[0])):
#                 dataset[0].append(tmp[0][i])
#                 dataset[1].append(tmp[1][i])
#                 dataset[2].append(sum(tmp[2][i]))  # GED

#                 if len(dataset[0]) == batch_size:
#                     yield dataset
#                     dataset = [[], [], []]

#     if len(dataset[0]) > 0:
#         yield dataset
#     # print("time: ", time.time() - start)   
    
             
# 데이터를 메모리에 로드하는 함수
def load_data_to_memory(data_folder):
    dataset = [[], [], []]

    # 전체 파일 목록을 가져옵니다.
    all_files = []
    for foldername in os.listdir(data_folder):
        file_names = os.listdir(os.path.join(data_folder, foldername))
        all_files.extend([os.path.join(data_folder, foldername, filename) for filename in file_names])

    # 파일 목록을 셔플하거나 다른 방식으로 조정할 수 있습니다.
    random.shuffle(all_files)
    print("len(all_files): ", len(all_files))
    # all_files = all_files[:3]

    start = time.time()
    for file_path in all_files:
        with open(file_path, "rb") as fr:
            tmp = pickle.load(fr)
            for i in range(len(tmp[0])):
                dataset[0].append(tmp[0][i])
                dataset[1].append(tmp[1][i])
                dataset[2].append(sum(tmp[2][i]))  # GED

    print("Data loaded to memory. Time: ", time.time() - start)
    return dataset


def train(args, model, data_generator, epochNum):
    """Train the embedding model.
    args: Commandline arguments - conigf.py
    data_generator: Generator yielding batches of data
    """
    scheduler, opt = utils.build_optimizer(args, model.parameters())
    if args.method_type == "gnn":
        clf_opt = optim.Adam(model.clf_model.parameters(), lr=args.lr)

    model.train()  # dropout 및 batch normalization 활성화
    model.zero_grad()  # 학습하기 위한 Gradient 저장 변수 초기화
    
    best_loss = float('inf')  # 가장 작은 손실 초기값 설정
    best_model = None  # 가장 작은 손실을 갖는 모델 저장 변수

    for batch_idx, (pos_a, pos_b, pos_label) in enumerate(data_generator):
        print("epochNum:  ", epochNum)
        print("len(pos_a): ", len(pos_a))
        pos_a = batch_nx_graphs_rpe(pos_a)        
        pos_b = batch_nx_graphs_rpe(pos_b)
        pos_label = torch.tensor(pos_label, dtype=torch.float32).to(utils.get_device())

        emb_as, emb_bs = model.emb_model(pos_a), model.emb_model(pos_b)

        intersect_embs = None
        pred = model(emb_as, emb_bs)
        emb_as, emb_bs = pred

        loss = model.criterion(pred, intersect_embs, pos_label)
        print("Batch {}, Loss: {:.4f}".format(batch_idx, loss.item()))

        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)

        opt.step()
        if scheduler:
            scheduler.step()

        if args.method_type == "gnn":
            with torch.no_grad():
                pred = model.predict(pred)
            model.clf_model.zero_grad()
            pred = model.clf_model(pred.unsqueeze(1)).view(-1)
            criterion = nn.L1Loss()
            clf_loss = criterion(pred.float(), pos_label.float())
            clf_loss.backward()
            clf_opt.step()
        
        if loss.item() < best_loss:
            # 현재 손실이 이전 최고 손실보다 작으면 모델 저장
            best_loss = loss.item()
            best_model = model.state_dict()

        if batch_idx >= args.max_batches:
            break
        
    # 1 에포크가 끝날 때마다 가장 작은 손실을 갖는 모델 저장
    if best_model is not None:
        # torch.save(best_model, args.model_path)
        print("Saving {}".format(args.model_path[:-3]+"_e"+str(epochNum)+".pt"))
        print("best loss: ",best_loss)
        torch.save(best_model, 
        args.model_path[:-3]+"_best_e"+str(epochNum+1)+".pt")
    
    
# 수정된 data_generator 함수 (메모리에서 데이터 가져오도록 변경)
def data_generator_from_memory(data_in_memory, batch_size):
    dataset = data_in_memory  # 메모리에 로드한 데이터를 사용
    num_samples = len(dataset[0])
    start_idx = 0

    while start_idx < num_samples:
        end_idx = min(start_idx + batch_size, num_samples)
        batch_data = [dataset[0][start_idx:end_idx], dataset[1][start_idx:end_idx], dataset[2][start_idx:end_idx]]
        yield batch_data
        start_idx = end_idx
        
        

def train_loop(args):
    print("utils.get_device() : ", utils.get_device())
    if not os.path.exists(os.path.dirname(args.model_path)):
        os.makedirs(os.path.dirname(args.model_path))
    if not os.path.exists("plots/"):
        os.makedirs("plots/")

    model = build_model(args)
    data_folder = 'data/train/'
    batch_size = args.batch_size
    max_epoch = 200
    # data_gen = data_generator(data_folder, batch_size)
   
    # 데이터를 메모리에 로드
    data_in_memory = load_data_to_memory(data_folder)

    max_batches = args.max_batches
    for epoch in range(max_epoch):
        start = time.time()
        print("epoch : ", epoch)

        # 데이터를 메모리에서 가져와서 사용
        data_gen = data_generator_from_memory(data_in_memory, batch_size)
        train(args, model, data_gen, epoch)
        torch.save(model.state_dict(), args.model_path[:-7] + "_allepoch_e" + str(epoch + 1) + ".pt")

        print("time: ", time.time() - start)


def main(force_test=False):
    parser = argparse.ArgumentParser(description='Embedding arguments')
    parser.add_argument('--max_batches', type=int, default=1000, help='Maximum number of batches to train on')
    

    utils.parse_optimizer(parser)
    parse_encoder(parser)
    args = parser.parse_args()

    if force_test:
        args.test = True
    train_loop(args)


if __name__ == '__main__':
    main()