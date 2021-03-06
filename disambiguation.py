#!/usr/bin/env python
#-*-coding:utf-8-*-

import nltk
import string
import math
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import jieba

from collections import Counter

from model.query import Query
from db import *
from WordsSplit import SplitByLanguage


def normalize(d):
    a = d.values()
    n = len(a)
    mean = sum(a) / n
    std = math.sqrt(sum((x-mean)**2 for x in a) / n)

    for k, v in d.items():
        meanRemoved = v - mean #减去均值  
        stded = meanRemoved / (std+1) #用标准差归一化  
        d[k] = stded
    return d

################# Strategy ####################
def context_sim(mention, cans, doc, db, num=0, threshold=None):
    """
    Compare context of comment and abstract of entity 
    """
    c_sim = {}
    
    def similar_cal(t, cans):
#         print ("candiates:" + ' '+candidates)
        for c in cans:
            print (c)
            a = db.get_abstract(c)
            if a:
                print (c+' ' +'has abstract')

                seg_list = jieba.cut(t, cut_all=False)
                t = " ".join(seg_list)
                seg_list = jieba.cut(a, cut_all=False)
                a = " ".join(seg_list)

                try:
                    c_sim[c] = similarity(t, a)
                except:
                    c_sim[c] = 0.0


                for k,v in c_sim.items():
                    print (k +' ' + str(v))
            else:
                c_sim[c] = 0.0

    def similarity(t1, t2):
        return Distance.cosine_distance(t1.lower(), t2.lower());
    #if len(self.candidates) == 1:
    #    return self.candidates[0]

    similar_cal(doc, cans)

    if threshold:
        for k,v in c_sim.items():
            if v < threshold:
                c_sim.popitem(k)

    return c_sim

def ranking(db,mention,context,location,cans,movie_id,movie_commented,threshold=None):
    """
            利用被评论电影的信息进行ranking
    """
    def movie2movie_sim(m1,m2):
        es = set()
        for key in m1:
            if key not in ("description/zh","summary","image","instanceOf","firstimage","imdb","topic_equivalent_webpage") :
                if key in m2:
                    if key != "actor_list":
                        common = list(set(m1[key])&set(m2[key]))
                        if len(common) :
                            es.add(common[0])
                        
#                     print(key + ":" +str(m1[key]))
#                     print(key + ":" +str(m2[key]))
#                     print(set(m1[key])&set(m2[key]))
                    else:
                        es = es.union(set(m1[key])&set(m2[key]))
        return es
    
#     movie_commented = db.get_whole_info_label(movie_id)
#    print(movie_commented)
#    print(db)
    c_sim = {}
    c_info = {}
    for c in  cans:
#         print("Can ID: " + c)
        can_obj = db.get_whole_info_label(c)
#	print(can_obj.get("instanceOf",[]))
        es1 = set()#两个电影比较，共现属性名集合
        es2 = set()#人物与电影比较，该人物出现在电影相应人物属性列表中则进该集合，权重*8
        es3 = set()#候选实体为人物，进该集合。权重*2
        es4 = set()#放在各种括号内的实体一定要加分 权重 *4
        
        if (location > 0) and (location + len(mention) < len(context)):
            if context[location-1] ==u"《" and context[location + len(mention)] ==u"》":
                es4.add(mention)
            elif context[location-1] == u"(" and context[location + len(mention)] ==u")":
                es4.add(mention)
            elif context[location-1] == u"【" and context[location + len(mention)] ==u"】":
                es4.add(mention)
            elif context[location-1] == u"（" and context[location + len(mention)] ==u"）":
                es4.add(mention)
            elif context[location-1] == u"[" and context[location + len(mention)] ==u"]":
                es4.add(mention)
            elif context[location-1] == u"#" and context[location + len(mention)] ==u"#":
                es4.add(mention)
                
        if u'电影' in can_obj.get("instanceOf",[]) or u'电视' in can_obj.get("instanceOf",[]):
            es1 = movie2movie_sim(movie_commented,can_obj)
        if u'演员' in can_obj.get("instanceOf",[]):
            if mention in can_obj.get("label/zh",[]) :#候选实体为人物，且mention与该候选实体的正名相同
                es3.add(mention)
            for item in can_obj.get("label/zh",[]):
#                 if item in movie_commented["actor_list"]:
                if item in movie_commented.get("actor_list",[]):
                    es2.add(item)
            for item in can_obj.get("alias",[]):
                if item in movie_commented.get("actor_list",[]):
                    es2.add(item) 
                
        if u'导演' in can_obj.get("instanceOf",[]):
            if mention in can_obj.get("label/zh",[])  :
                es3.add(mention)
            for item in can_obj.get("label/zh",[]):
#                 if item in movie_commented["directed_by"]:
                if item in movie_commented.get("directed_by",[]):
                    es2.add(item)
            for item in can_obj.get("alias",[]):
                if item in movie_commented.get("directed_by",[]):
                    es2.add(item)
        if u'制片人' in can_obj.get("instanceOf",[]):
            if mention in can_obj.get("label/zh",[])  :
                es3.add(mention)
            for item in can_obj.get("label/zh",[]):
#                 if item in movie_commented["produced_by"]:
                if item in movie_commented.get("produced_by",[]):
                    es2.add(item)
            for item in can_obj.get("alias",[]):
                if item in movie_commented.get("produced_by",[]):
                    es2.add(item)
        if u'编剧' in can_obj.get("instanceOf",[]):
            if mention in can_obj.get("label/zh",[])  :
                es3.add(mention)
            for item in can_obj.get("label/zh",[]):
                if item in movie_commented.get("written_by",[]):
                    es2.add(item)
            for item in can_obj.get("alias",[]):
                if item in movie_commented.get("written_by",[]):
                    es2.add(item)
        if u'摄影师' in can_obj.get("instanceOf",[]):
            if mention in can_obj.get("label/zh",[])  :
                es3.add(mention)
            for item in can_obj.get("label/zh",[]):
                if item in movie_commented.get("cinematograph_by",[]):
                    es2.add(item)
            for item in can_obj.get("alias",[]):
                if item in movie_commented.get("cinematograph_by",[]):
                    es2.add(item)
        if u'音乐指导' in can_obj.get("instanceOf",[]):
            if mention in can_obj.get("label/zh",[]) :
                es3.add(mention)
            for item in can_obj.get("label/zh",[]):
                if item in movie_commented.get("music_by",[]):
                    es2.add(item)
            for item in can_obj.get("alias",[]):
                if item in movie_commented.get("music_by",[]):
                    es2.add(item)
        if u'主持人' in can_obj.get("instanceOf",[]):
            if mention in can_obj.get("label/zh",[])  :
                es3.add(mention)
            for item in can_obj.get("label/zh",[]):
                if item in movie_commented.get("presenter",[]):
                    es2.add(item)
            for item in can_obj.get("alias",[]):
                if item in movie_commented.get("presenter",[]):
                    es2.add(item)
        if u'配音' in can_obj.get("instanceOf",[]):
            if mention in can_obj.get("label/zh",[])  :
                es3.add(mention)
            for item in can_obj.get("label/zh",[]):
                if item in movie_commented.get("dubbing_performances",[]):
                    es2.add(item)
            for item in can_obj.get("alias",[]):
                if item in movie_commented.get("dubbing_performances",[]):
                    es2.add(item)
        c_sim[c] = (len(es1)+8*len(es2)+2*len(es3)+4*len(es4),es1,es2,es3,es4)
        c_info[c] = can_obj.get("label/zh",[""])[0]
        
#     for k,v in c_sim.items():
#         print (k+" "+str(v))
        #c_sim[k] = v*1.0/len(mentions)
#         c_sim[k] = v*1.0/len(context_mentions)

    #c_sim = normalize(c_sim)

    if threshold:
        for k,v in list(c_sim.items()):
            if v[0] < threshold:
                c_sim.pop(k)
                c_info.pop(k)


    return (c_info,c_sim)
            
        
    
    
def entity_cooccur(db, mention, mentions, context_mentions,cans, threshold=None):
    """
    """

    c_sim = {}
    mentions = set(mentions)
    context_mentions = set(context_mentions)

    for c in cans:
        print ("Can ID:"+c)
        es = db.get_prop_entities(c)
        print ("    Entities in graph:")
        print ("    "+",".join(es))
        if not es or len(es) == 0:
            c_sim[c] = 0.0
        else:
            print ("    common: "+",".join(set(context_mentions)&set(es)))
            c_sim[c] = len(set(context_mentions)&set(es))

    for k,v in c_sim.items():
        print (k+" "+str(v))
        #c_sim[k] = v*1.0/len(mentions)
        c_sim[k] = v*1.0/len(context_mentions)

    #c_sim = normalize(c_sim)

    if threshold:
        for k,v in list(c_sim.items()):
            if v < threshold:
                c_sim.pop(k)


    return c_sim

class Disambiguation():

    def __init__(self, func=None, args={}):

        if not func:
            raise ValueError("Not add strategy")
        self.func = func
        self.args = args

    def get_best(self):
        import operator
        c_sim = self.func(**self.args)
        if len(c_sim) == 0:
            return {}
        best = max(c_sim.items(), key=operator.itemgetter(1))
        return [best]

    def get_sorted_cans(self, num=0):
        """
        Returns:
            return all candidate with their similarity
        """

        (c_info,c_sim) = self.func(**self.args)

        best = sorted(c_sim.items(), key=lambda x:x[1][0], reverse=True)
        if num:
            return best[:num],c_info
        else:
            return best,c_info


class Distance():

    @staticmethod
    def cosine_distance(t1, t2):
        """
        Return the cosine distance between two strings
        """

        def cosine(u, v):
            """
            Returns the cosine of the angle between vectors v and u. This is equal to u.v / |u||v|.
            """
            import numpy
            import math
            return numpy.dot(u, v) / (math.sqrt(numpy.dot(u, u)) * math.sqrt(numpy.dot(v, v)))

        tp = TextProcesser()
        c1 = dict(tp.get_count(t1))
        c2 = dict(tp.get_count(t2))
        keys = c1.keys() + c2.keys()
        word_set = set(keys)
        words = list(word_set)
        v1 = [c1.get(w,0) for w in words]
        v2 = [c2.get(w,0) for w in words]
        return cosine(v1, v2)

    @staticmethod
    def levenshtein(first, second):
        """
        Edit Distance
        """
        if len(first) > len(second):
            first,second = second,first
        if len(first) == 0:
            return len(second)
        if len(second) == 0:
            return len(first)
        first_length = len(first) + 1
        second_length = len(second) + 1
        distance_matrix = [range(second_length) for x in range(first_length)]
        #print distance_matrix 
        for i in range(1,first_length):
            for j in range(1,second_length):
                deletion = distance_matrix[i-1][j] + 1
                insertion = distance_matrix[i][j-1] + 1
                substitution = distance_matrix[i-1][j-1]
                if first[i-1] != second[j-1]:
                    substitution += 1
                distance_matrix[i][j] = min(insertion,deletion,substitution)
        return distance_matrix[first_length-1][second_length-1]


class TextProcesser():

    def __init__(self):
        pass

    def get_tokens(self, t):
        lowers = t.lower()
        #remove the punctuation using the character deletion step of translate
        #no_punctuation = lowers.translate(None, string.punctuation)
        no_punctuation = lowers.translate(string.punctuation)
        tokens = nltk.word_tokenize(no_punctuation)
        from nltk.corpus import stopwords
        tokens = [w for w in tokens if not w in stopwords.words('english')]
        return tokens

    def stem_tokens(self, tokens, stemmer):
        stemmed = []
        for item in tokens:
            stemmed.append(stemmer.stem(item))
        return stemmed

    def get_count(self, t):
        return Counter(self.get_tokens(t)).most_common()


