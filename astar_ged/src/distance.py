from astar_ged.src.utils import get_root_path, exec, get_ts
from astar_ged.src.nx_to_gxl import nx_to_gxl
from os.path import isfile
from os import getpid
import fileinput
import networkx as nx
import numpy as np

import sys


def mcs(g1, g2):
    nx.write_gexf(g1, 'temp_1.gexf')
    nx.write_gexf(g2, 'temp_2.gexf')
    # Force using bash instead of dash.
    # `source activate` does not work on dash.
    # graphembedding is a virtual python environment with networkx==2.0.
    # By default networkx==1.10 is assumed.
    cmd = 'source activate graphembedding && python mcs_cal.py'
    exec('/bin/bash -c "{}"'.format(cmd))
    f = open('mcs_result.txt', 'r')
    return int(f.read())


def ged(g1, g2, algo, debug=False, timeit=False):
    # https://github.com/dan-zam/graph-matching-toolkit
    gp = get_gmt_path()
    append_str = get_append_str(g1, g2)
    src, t_datapath = setup_temp_data_folder(gp, append_str) 

    meta1 = write_to_temp(g1, t_datapath, algo, 'g1')
    meta2 = write_to_temp(g2, t_datapath, algo, 'g2')
    if meta1 != meta2:
        raise RuntimeError(
            'Different meta data {} vs {}'.format(meta1, meta2)
            )
    prop_file = setup_property_file(src, gp, meta1, append_str)
    
    
    
   #   print("prop_file: ", prop_file)
   #   print("meta1: ", meta1)
  #    print("meta2: ", meta2)

    #  print("t_datapath: ", t_datapath)
    #  print("src: ", src)
   #   print("append_str: ", append_str)
   #   print("gp: ", gp)

    rtn = []
    # print(gp)
    # print(get_root_path())
    # print(append_str)
    if not exec(
            'cd {} && java {}'
            ' -classpath {}/src/graph-matching-toolkit/graph-matching-toolkit.jar algorithms.GraphMatching '
            './properties/properties_temp_{}.prop'.format(
                gp, '-XX:-UseGCOverheadLimit -XX:+UseConcMarkSweepGC -Xmx100g'
                if algo == 'astar' else '', get_root_path(), append_str)):
        rtn.append(-1)
    else:
        d, result_file = get_result(gp, algo, append_str)
    '''
        rtn.append(d)
        if g1size != g1.number_of_nodes():
            print('g1size {} g1.number_of_nodes() {}'.format(g1size, g1.number_of_nodes()))
        assert (g1size == g1.number_of_nodes())
        assert (g2size == g2.number_of_nodes())
    if debug:
        rtn += [lcnt, g1, g2]
    if timeit:
        rtn.append(t)
    clean_up(t_datapath, prop_file, result_file)
    if len(rtn) == 1:
        return rtn[0]
    return tuple(rtn)
    '''
    clean_up(t_datapath, prop_file, result_file)
    return d


def normalized_ged(d, g1, g2):
    return 2 * d / (g1.number_of_nodes() + g2.number_of_nodes())

def unnormalized_ged(d, g1, g2):
    return d * (g1.number_of_nodes() + g2.number_of_nodes()) / 2


def setup_temp_data_folder(gp, append_str):
    tp = gp + '/data/temp_{}'.format(append_str)
    exec('rm -rf {} && mkdir {}'.format(tp, tp))
    src = get_root_path() + '/src/gmt_files'
    exec('cp {}/temp.xml {}/temp_{}.xml'.format(src, tp, append_str))
    return src, tp


def write_to_temp(g, tp, algo, g_name):
    node_attres, edge_attrs = nx_to_gxl(g, g_name,
                                        '{}/{}.gxl'.format(tp, g_name))
#    print("==============")
#    print("node_attres:", node_attres)
#    print("edge_attrs:", edge_attrs)
#    print("g:", g)
#    print("g_name:", g_name)
#    print(" / format(tp, g_name):", '{}/{}.gxl'.format(tp, g_name))
#    print("tp:", tp)
#    print("meta: ", algo + '_' + '_'.join(sorted(list(node_attres.keys())) +
#                                 sorted(list(edge_attrs.keys()))))   # -> 해당 이름으로 prop 파일 만들어주면됨

    return algo + '_' + '_'.join(sorted(list(node_attres.keys())) +
                                 sorted(list(edge_attrs.keys())))


def setup_property_file(src, gp, meta, append_str):
    destfile = '{}/properties/properties_temp_{}.prop'.format(
        gp, append_str)
    srcfile = '{}/{}.prop'.format(src, meta)
    # print(destfile)
    # print(srcfile)
    if not isfile(srcfile):
        if 'beam' in meta:  # for beam
            metasp = meta.split('_')
            s = int(metasp[0][4:])
            if s <= 0:
                raise RuntimeError('Invalid s for beam search: {}'.format(s))
            newmeta = '_'.join(['beam'] + metasp[1:])
            srcfile = '{}/{}.prop'.format(src, newmeta)
        else:
            raise RuntimeError('File {} does not exist'.format(srcfile))
    exec('cp {} {}'.format(srcfile, destfile))
    for line in fileinput.input(destfile, inplace=True):
        line = line.rstrip()
        if line == 's=':  # for beam
            print('s={}'.format(s))
        else:
            print(line.replace('temp', 'temp_{}'.format(append_str)))
    return destfile


def get_result(gp, algo, append_str):
    result_file = '{}/result/temp_{}'.format(gp, append_str)  # 해당 파일에서 값이 있는 line으로 지정 필요
    with open(result_file) as f:
        lines = f.readlines()
        #ln = 16 if 'beam' in algo else 15
        # t = int(lines[ln].split(': ')[1])  # msec
        
        #ln = 23 if 'beam' in algo else 23  #f0
        ln = 27 if 'beam' in algo else 27  # f0 r0
        d = float(lines[ln]) * 2  # alpha=0.5 --> / 2
        return d, result_file


def get_gmt_path():
    return get_root_path() + '/src/graph-matching-toolkit'


def get_append_str(g1, g2):
    return '{}_{}_{}_{}'.format(
        get_ts(), getpid(), g1.graph['gid'], g2.graph['gid'])


def clean_up(t_datapath, prop_file, result_file):
    for path in [t_datapath, prop_file, result_file]:
        exec('rm -rf {}'.format(path))


if __name__ == '__main__':
    from utils import load_data

    test_data = load_data('linux', train=False)
    train_data = load_data('linux', train=True)
    g1 = train_data.graphs[0]
    g2 = test_data.graphs[0]
    print(mcs(g1, g2))

    # g1 = test_data.graphs[15]
    # g2 = train_data.graphs[761]
    #
    # # nx.write_gexf(g1, get_root_path() + '/temp/g1.gexf')
    # # nx.write_gexf(g2, get_root_path() + '/temp/g2.gexf')
    # g1 = nx.read_gexf(get_root_path() + '/temp/g1_small.gexf')
    # g2 = nx.read_gexf(get_root_path() + '/temp/g2_small.gexf')
    # print(astar_ged(g1, g2))
    # print(beam_ged(g1, g2, 2))
