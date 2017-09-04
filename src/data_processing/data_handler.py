from collections import defaultdict
import re
from gensim.models.word2vec import Word2Vec
import numpy
from nltk.tokenize import TweetTokenizer
from nltk.corpus import stopwords
import gensim
import nltk
import data_processing.glove2Word2vecLoader as glove



def load_word2vec(lang = 'en',path = '/home/word2vec/GoogleNews-vectors-negative300.bin'):
    word2vecmodel = None
    if(lang=='en'):
        word2vecmodel = gensim.models.KeyedVectors.load_word2vec_format(path,
                                                          binary=True)
    if(lang=='de'):
        word2vecmodel = gensim.models.KeyedVectors.load_word2vec_format('/home/word2vec/german_word2vec.bin', binary=True)

    return word2vecmodel

def InitializeWords(word_file_path):
    words=set()
    content = open(word_file_path).readlines()
    words.update([word for word in content])
    return words

def normalize_word(word):
    temp = word
    while True:
        w = re.sub(r"([a-zA-Z])\1\1", r"\1\1", temp)
        if (w == temp):
            break
        else:
            temp = w
    return w

def split_ht(term, wordlist):
    words = []
    if (term != term.lower() and term != term.upper()):
        words = re.findall('[A-Z][^A-Z]*', term)
    else:
        j = 0
        while (j <= len(term)):
            loc = j
            for i in range(j + 1, len(term) + 1, 1):
                if (wordlist.__contains__(term[j:i].lower())):
                    loc = i

            if (loc == j):
                j += 1
            else:
                words.append(term[j:loc])
                j = loc
    words = ["#" + str(s) for s in words]
    return words

def filter_text(text, word_list, normalize_text=False, split_hashtag=False, ignore_profiles=False, lowercase =False):
    filtered_text = []
    # print(text)
    for t in text:
        splits=None
        if(ignore_profiles and str(t).startswith("@")):
            continue

        if(str(t).startswith('http')):
            continue

        if (str(t).lower() == '#sarcasm'):
            continue

        #removes repeatation of letters
        if (normalize_text):
            t = normalize_word(t)

        if (split_hashtag and str(t).startswith("#")):
            splits = split_ht(t, word_list)

        #appends the text
        if(lowercase==True):
            t=t.lower()

        filtered_text.append(t)

        if (splits != None):
            filtered_text.extend([s for s in splits if (not filtered_text.__contains__(s))])

    return filtered_text

def parsedata(lines, word_list, normalize_text=False, split_hashtag=False, ignore_profiles=False,lowercase =False):
    data = []
    for line in lines:
        try:
            token = line.split('\t')
            # print(line)

            label = int(token[1].strip())

            target_text = TweetTokenizer().tokenize(token[2].strip())

            # filter text
            target_text = filter_text(target_text, word_list, normalize_text, split_hashtag, ignore_profiles,lowercase=lowercase)
            # print(filtered_text)


            dimensions= []
            if(len(token)>3 and token[3].strip()!='NA'):
                d = defaultdict()
                for dimension in token[3].strip().split('|'):
                    d[dimension.split('@@')[0]] = dimension.split('@@')[1]

                dimensions =[d.get(di) for di in ['Sensory','Plugged_In','Depressed','Angry','Spacy/Valley_girl','Worried','Arrogant/Distant','Analytic','In-the-moment','Upbeat','Personable']]

            context = []
            if(len(token)>4):
                if(token[4]!='NA'):
                    context = TweetTokenizer().tokenize(token[4].strip())
                    context = filter_text(context, word_list, normalize_text, split_hashtag, ignore_profiles=True,lowercase=lowercase)

            author = 'NA'
            if(len(token)>5):
                author=token[5]

            if(len(target_text)!=0):
                # print((label, target_text, dimensions, context, author))
                data.append((label, target_text, dimensions, context, author))
        except:
            raise
            # print('error', line)
    return data

def loaddata(filename, word_file_path, normalize_text=False, split_hashtag=False, ignore_profiles=False,lowercase =False):
    word_list = None
    if (split_hashtag):
        word_list = InitializeWords(word_file_path)

    lines = open(filename,'r').readlines()
    data = parsedata(lines, word_list, normalize_text=normalize_text, split_hashtag=split_hashtag, ignore_profiles=ignore_profiles,lowercase=lowercase)
    return data

def build_vocab(data, without_dimension=True, skip_words = False, ignore_context = False):
    #keep total words for speed
    vocab = defaultdict(int)

    st_words = set()
    is_noun = lambda pos: pos[:2] == 'NN'
    is_verb = lambda pos: pos[:2] == 'VB'

    total_words = 1
    # if(not without_dimension):
    for i in range(1,101):
        vocab[str(i)] = total_words
        total_words = total_words + 1

    for sentence_no, token in enumerate(data):
        # print(token[1])
        if (skip_words):
            pos_tagged = nltk.pos_tag(nltk.word_tokenize(' '.join(token[1])))
            # words = [word for (word, pos) in pos_tagged]
            nouns = [word for (word, pos) in pos_tagged if is_noun(pos)]
            verbs = [word for (word, pos) in pos_tagged if is_verb(pos)]
            st_words.update(nouns)
            st_words.update(verbs)

        for word in token[1]:
            if(st_words.__contains__(word.lower())):
                continue
            if(not word in vocab):
                vocab[word] = total_words
                total_words = total_words + 1

        if(not without_dimension):
            for word in token[2]:
                if (st_words.__contains__(word.lower())):
                    continue
                if(not word in vocab):
                    vocab[word] = total_words
                    total_words = total_words + 1

        if(ignore_context==False):
            for word in token[3]:
                if(not word in vocab):
                    if (st_words.__contains__(word.lower())):
                        continue
                    vocab[word] = total_words
                    total_words = total_words + 1
    return vocab

def build_reverse_vocab(vocab):
    rev_vocab = defaultdict(str)
    for k, v in vocab.items():
        rev_vocab[v]=k
    return rev_vocab

def vectorize_word_dimension(data, vocab, drop_dimension_index = None):
    X = []
    Y = []
    D = []
    C = []
    A = []

    for label, line, dimensions, context, author in data:
        vec=[]
        context_vec=[]

        if(len(dimensions)!=0):
            dvec = [int(d) for d in dimensions]
        else:
            dvec = [0]*11

        if drop_dimension_index!=None:
            dvec.pop(drop_dimension_index)

        for words in line:
            if(words in vocab):
                vec.append(vocab[words])
            else:
                vec.append(vocab['unk'])

        if(len(context)!=0):
            for words in context:
                if(words in vocab):
                    context_vec.append(vocab[words])
                else:
                    context_vec.append(vocab['unk'])
        else:
            context_vec = [vocab['unk']]

        X.append(vec)
        Y.append(label)
        D.append(dvec)
        C.append(context_vec)
        A.append(author)

    return numpy.asarray(X), numpy.asarray(Y), numpy.asarray(D), numpy.asarray(C), numpy.asarray(A)

def pad_sequence_1d(sequences, maxlen=None, dtype='float32', padding='pre', truncating='pre', value=0.):
    X = [vectors for vectors in sequences]

    nb_samples = len(X)


    x = (numpy.ones((nb_samples, maxlen)) * value).astype(dtype)

    for idx, s in enumerate(X):
        if truncating == 'pre':
            trunc = s[-maxlen:]
        elif truncating == 'post':
            trunc = s[:maxlen]
        else:
            raise ValueError("Truncating type '%s' not understood" % padding)

        if padding == 'post':
            x[idx, :len(trunc)] = trunc
        elif padding == 'pre':
            x[idx, -len(trunc):] = trunc
        else:
            raise ValueError("Padding type '%s' not understood" % padding)

    return x

def write_vocab(filepath,vocab):
    with open(filepath, 'w') as fw:
        for key, value in vocab.items():
            fw.write(str(key) + '\t' + str(value) + '\n')

def get_word2vec_weight(vocab,n=300,lang = 'en',path = '/home/word2vec/GoogleNews-vectors-negative300.bin'):
    word2vecmodel = load_word2vec(lang=lang,path=path)
    emb_weights= numpy.zeros((len(vocab.keys())+1,n))
    for k,v in vocab.items():
        if(word2vecmodel.__contains__(k)):
            emb_weights[v,:]=word2vecmodel[k][:n]

    return emb_weights


def load_glove_model(vocab,n=200):
    word2vecmodel = glove.load_glove_word2vec('/home/glove/glove.twitter.27B/glove.twitter.27B.200d.txt')

    emb_weights = numpy.zeros((len(vocab.keys()) + 1, n))
    for k, v in vocab.items():
        if (word2vecmodel.__contains__(k)):
            emb_weights[v, :] = word2vecmodel[k][:n]

    return emb_weights
