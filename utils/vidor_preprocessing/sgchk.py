import networkx as nx
import pickle
import os, sys
from tqdm import tqdm


# with open('data/Vidor/scenegraph/0_2754378442_6188920051.pkl', 'rb') as fr:
#   data = pickle.load(fr)
# print(data[0][0])
# print(len(data[0]))
# print(len(data[0][0]))

# for video in data[0]:
#   for graph in video:
#     if len(graph) != 0:
#       print(len(graph))

# ------------------------------
# with open('data/Vidor/scenegraph/merge_scenegraphs.pkl', 'rb') as fr:
#   data = pickle.load(fr)

# cnt = 0
# for graphs in tqdm(data[0]) :
#   cnt += len(graphs)
# print("cnt: ",cnt)


# sys.exit()
# ------------------------------
# with open('data/Vidor/scenegraph/merge_scenegraphs', 'rb') as fr:
#   data = pickle.load(fr)

# cnt = 0
# for graphs in tqdm(data[0]):
#   cnt += len(graphs)
# print("cnt: ",cnt)


# # #fid graph 에 tag 넣어야하는데 노드에 넣을건가?
path_to_folder = 'data/scenegraph/'  
file_list = os.listdir(path_to_folder)

listIdx = len(file_list)//4

file_list1 = file_list[:listIdx]
file_list2 = file_list[listIdx : listIdx*2]
file_list3 = file_list[listIdx*2 : listIdx*3]
file_list4 = file_list[listIdx*3 :]
target_list = [file_list1, file_list2, file_list3, file_list4]


for idx, file_list_name in enumerate(target_list): # 파일 명 
  cnt = 0
  upper5Graph = []
  totalFileNameList = []
  #file list의 file name을 기반으로 읽어서 노드의 개수가 다섯개 이상인 것들만..!
  for file_name in tqdm(file_list_name): # 파일 명 
    with open(os.path.join(path_to_folder,file_name), "rb") as fr:
      data = pickle.load(fr) 
      scenegraphs = data[0]
      for idx2, videojson in enumerate(scenegraphs): #5개 파일에 대한 scenegraph list
        video = []
        fileNameList = []
        for graph in videojson:
          if len(graph) !=0 : #한개 json의 frame 한 개 = scene graph 1개
            video.append(graph)
            fileNameList.append(data[1][idx2])
        if len(video) != 0:
          cnt += len(video)
          upper5Graph.append(video)
          totalFileNameList.append(fileNameList)

  with open('data/scenegraph_merge/merge_scenegraphs_{}.pkl'.format(idx), 'wb') as f:
          pickle.dump((upper5Graph, totalFileNameList), f)

  print("cnt: ", cnt)
  print("len(upper5Graph) :",len(upper5Graph))
  print("len(totalFileNameList) :",len(totalFileNameList))
  