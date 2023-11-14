import unittest

from rethink.models.search.idf import tfidf

docs = {
    "1": "The stop_words_ attribute can get large and increase the model size when pickling. This attribute is provided"
         " only for introspection and can be safely removed using delattr or set to None before pickling.",
    "2": "为(B, M, E, S): {B:begin, M:middle, E:end, S:single}。"
         "分别代表每个状态代表的是该字在词语中的位置，B代表该字是词语中的起始字，M代表是词语中的中间字，E代表是词语中的结束字，"
         "S则代表是单字成词。",
    "3": "我们在这个短片简介中提到过。 机器怎么理解句子一直是一个难题，以前有人尝试将用句子中出现的词语频率来表达这个句子的含义（TF-IDF）。"
         " 也有人想把句子中的词语先向量化，然后再叠加句子中所有向量化的词语来表达一句话。"
         " 这些在的确都是一种计算机表达句子含义的方式，"
         "但是不一定会非常准确。因为他们都只是一种对词语理解的简单加工方式，"
         "有的忽略了词语的表达顺序， 有的忽略了词语的组合模式。这往往导致计算机不能非常准确的理解句子。",
    "4": "我们在这个短片简介中提到过。 机器怎么理解句子一直是一个难题，"
         "以前有人尝试将用句子中出现的词语频率来表达这个句子的含义（TF-IDF）。",
    "5": "The hospital was built in 2011 with donations from Indonesian citizens and organisations,"
         " including the Indonesian Red Cross Society and"
         " the Muhammadiyah Society, one of Indonesia’s largest "
         "Muslim organisations. It was officially inaugurated in "
         "2016 by the then-Indonesian vice president, Jusuf Kalla. Three Indonesian volunteers with the "
         "Indonesian humanitarian organisation the Medical Emergency"
         " Rescue Committee (MER-C), which organised the "
         "donations to build the hospital, are currently based in north Gaza.",
    "6": "The hospital was built in 2011 with donations from Indonesian citizens and organisations,",

}


class TFIDFTest(unittest.TestCase):

    def test_tokenizer(self):
        for s, t in [
            ("计算机理解句子 apple is a fruit. ", ['计算', '算机', '计算机', '理解', '句子', 'apple', 'a', 'fruit']),
            ("wdasd dqwwq ffger 问答apple使用Python", ['wdasd', 'dqwwq', 'ffger', '问答', 'apple', '使用', 'python']),
            (
                    "The hospital was built in 2011 with donations from Indonesian citizens and organisations,",
                    ['hospital', 'was', 'built', '2011', 'donations', 'indonesian', 'citizens', 'organisations']
            ),
        ]:
            res = list(tfidf.tokenizer(s))
            self.assertEqual(t, res)

    def test_search(self):
        _ds = []
        nids = []
        for k, v in docs.items():
            _ds.append(v)
            nids.append(k)

        vec = tfidf.docs2vec(_ds)
        self.assertEqual((6, 555861), vec.shape)

        res = tfidf.search("计算机理解句子", docs_vec=vec, n=2)
        self.assertEqual(["3", "4"], [nids[i] for i in res])
        res = tfidf.search("hospital built", docs_vec=vec, n=2)
        self.assertEqual(["6", "5"], [nids[i] for i in res])
