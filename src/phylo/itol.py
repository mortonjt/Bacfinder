
"""
The purpose of this is to create phylogenetic trees through iTOL

Given 16SRNAs and a bunch of operons output the following

1. A fasttree for all of the species that have these operons
2. iTOL friendly format with 
   a. number of operons
   b. composition of functional genes
"""

import os,sys,site
base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for directory_name in os.listdir(base_path):
    site.addsitedir(os.path.join(base_path, directory_name))
import quorum
import subprocess
from Bio import SeqIO, SeqFeature
from Bio.SeqRecord import SeqRecord
from fasttree import *
from collections import *
class iTOL():
    
    def __init__(self,operonFile,allrrna,rrnaFile=None,alignFile=None,treeFile=None):
        
        self.operonFile = operonFile
        self.allrrna = allrrna
        basename = os.path.basename(operonFile)
        #Store RRNA fasta file
        if rrnaFile==None:
            self.rrnaFile = "%s.rrna"%basename
        else:
            self.rrnaFile = rrnaFile
            #For multiple alignment
        if alignFile == None:
            self.alignFile = "%s.align"%basename
        else:
            self.alignFile = alignFile    
        #For fasttree
        if treeFile == None:
            self.treeFile = "%s.tree"%basename
        else:
            self.treeFile = treeFile
        print self.rrnaFile
    def setOperonFile(self,operonFile):
        self.operonFile = operonFile
            
    def cleanUp(self):
        if os.path.exists(self.treeFile):
            os.remove(self.treeFile)
        if os.path.exists(self.rrnaFile):
            os.remove(self.rrnaFile)
        if os.path.exists(self.alignFile):
            os.remove(self.alignFile)
            
    """ Extract 16S rnas """
    def getRRNAs(self):
        rrnas = []
        seen = set()
        rrna_dict = SeqIO.to_dict(SeqIO.parse(open(self.allrrna,'r'), "fasta"))
        with open(self.operonFile,'r') as handle:
            for ln in handle:
                if ln[0]=="-": continue
                ln = ln.rstrip()
                toks = ln.split('|')
                acc,clrname,full_evalue,hmm_st,hmm_end,env_st,env_end,description=toks
                description = description.replace(' ','_')
                accession = acc.split('.')[0]
                if accession in rrna_dict:
                    if description not in seen:
                        record = rrna_dict[accession]
                        record.id = description
                        rrnas.append(record)
                        seen.add(description)
                else:
                    print "Accession %s is missing"%accession
        SeqIO.write(rrnas, open(self.rrnaFile,'w'), "fasta")
        
    """ Build fast tree """
    def buildTree(self,module=subprocess,iters=4,hours=12):
        ft = UnAlignedFastTree(self.rrnaFile,self.treeFile)
        ft.align(module=module,iters=10,hours=12) #Run multiple sequence alignment and spit out aligned fasta file
        proc=ft.run(module=module) #Run fasttree on multiple alignment and spit out newick tree
        proc.wait()
        ft.cleanUp() #Clean up!
        
    """ Pick top k biggest operons """
    def sizeFilter(self,filterout,k=100):
        
        buf = []
        outhandle = open(filterout,'w')
        lengths = []
        with open(self.operonFile,'r') as handle:
            for ln in handle:
                if ln[0]=='-':
                    lengths.append(len(buf))
                    buf = []                    
                else:
                    buf.append(ln)
        lengths = sorted(lengths,reverse=True)
        if k>len(lengths): threshold = lengths[-1]
        else:  threshold = lengths[k]
        with open(self.operonFile,'r') as handle:
            for ln in handle:
                if ln[0]=='-':
                    if len(buf)>threshold:
                        for line in buf:
                            outhandle.write(line)
                        outhandle.write("----------\n")
                    buf = []                    
                else:
                    buf.append(ln)
        outhandle.close()
        
    """ Spit out iTOL file for operon distribution """        
    def operonDistribution(self,itolout):
        outhandle = open(itolout,'w')
        outhandle.write("LABELS\timmunity\tmodifier\tregulator\ttoxin\ttransport\n")
        outhandle.write("COLORS\t#0000ff\t#00ff00\t#ff0000\t#ff00ff\t#ff8c00\n")    
        with open(self.operonFile,'r') as handle:
            func_counts = Counter({'immunity':0,'modifier':0,'regulator':0,'toxin':0,'transport':0,})
            prevName = None
            for ln in handle:
                if ln[0]=='-':continue
                toks = ln.split("|")
                acc,clrname,full_evalue,hmm_st,hmm_end,env_st,env_end,description=toks
                name = description.replace(' ','_')
                name = name.split(',')[0]
                if prevName == None: 
                    prevName = name 
                elif name!=prevName:
                    functions = func_counts.items()
                    functions = sorted(functions,key=lambda x:x[0])
                    prevName = prevName.rstrip()
                    functions,counts = zip(*functions)
                    outhandle.write("%s\t%s\n"%(prevName,'\t'.join(map(str,counts))))
                    func_counts = Counter({'immunity':0,'modifier':0,'regulator':0,'toxin':0,'transport':0,})
                    prevName = name
                function = clrname.split('.')[0]
                func_counts[function]+=1
        outhandle.close()
if __name__=="__main__":
    import unittest
    
    class TestiTOL(unittest.TestCase):
        def setUp(self):            
            self.rrnaFile="test.fa"
            self.operonFile = "test_operons.txt"
            self.ggtable = "../data/gg_13_5_accessions.txt"
            #self.accSeqs= "acc.fa"
            rrnas   = [">CP002059",
                       "AACGAACGCTGGCGGCATGCCTAACACATGCAAGTCGAACGAGACCTTCGGGTCTAGTGGCGCACGGGTGCGTAACGCGTGGGAATCTGCCCTTGGGTACGGAATAACAGTTAGAAATGACTGCTAATACCGTATAATGACTTCGGTCCAAAGATTTATCGCCCAGGGATGAGCCCGCGTAGGATTAGCTTGTTGGTGAGGTAAAGGCTCACCAAGGCGACGATCCTTAGCTGGTCTGAGAGGATGATCAGCCACACTGGGACTGAGACATGGCCCAGACTCCTACGGGAGGCAGCAGTGGGGAATATTGGACAATGGGCGAAAGCCTGATCCAGCAATGCCGCGTGAGTGATGAAGGCCTTAGGGTTGTAAAGCTCTTTTACCCGGGATGATAATGACAGTACCGGGAGAATAAGCCCCGGCTAACTCCGTGCCAGCAGCCGCGGTAATACGGAGGGGGCTAGCGTTGTTCGGAATTACTGGGCGTAAAGCGCACGTAGGCGGCTTTGTAAGTTAGAGGTGAAAGCCCGGGGCTCAACTCCGGAATTGCCTTTAAGACTGCATCGCTAGAATTGTGGAGAGGTGAGTGGAATTCCGAGTGTAGAGGTGAAATTCGTAGATATTCGGAAGAACACCAGTGGCGAAGGCGACTCACTGGACACATATTGACGCTGAGGTGCGAAAGCGTGGGGAGCAAACAGGATTAGATACCCTGGTAGTCCACGCCGTAAACGATGATGACTAGCTGTCGGGGCGCTTAGCGTTTCGGTGGCGCAGCTAACGCGTTAAGTCATCCGCCTGGGGAGTACGGCCGCAAGGTTAAAACTCAAAGAAATTGACGGGGGCCTGCACAAGCGGTGGAGCATGTGGTTTAATTCGAAGCAACGCGCAGAACCTTACCAGCGTTTGACATGGTAGGACGGTTTCCAGAGATGGATTCCTACCCTTACGGGACCTACACACAGGTGCTGCATGGCTGTCGTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGAGCGCAACCCTCGTCTTTGGTTGCTACCATTTAGTTGAGCACTCTAAAAAAACTGCCGGTGATAAGCCGGAGGAAGGTGGGGATGACGTCAAGTCCTCATAGCCCTTACGCGCTGGGCTACACACGTGCTACAATGGCGGTGACAGAGGGCAGCAAACCCGCGAGGGTGAGCTAATCTCCAAAAGCCGTCTCAGTTCGGATTGTTCTCTGCAACTCGAGAGCATGAAGGCGGAATCGCTAGTAATCGCGGATCAGCACGCCGCGGTGAATACGTTCCCAGGCCTTGTACACACCGCCCGTCACATCACGAAAGTCGGTTGCACTAGAAGTCGGTGGGCTAACCCGCAAGGGAGGCAGCCGCCTAAAGTGTGATCGGTAATTGGGGTG",
                       ">CP002069",
                       "AGAGTTTGATCCTGGCTCAGAATGAACGCTGGCGGCGTGCCTAACACATGCAAGTCGTACGAGAAATCCCGAGCTTGCTTGGGAAAGTAAAGTGGCGCACGGGTGAGTAACGCGTGGGTAACCCACCCCCGAATTCGGGATAACTCCGCGAAAGCGGTGCTAATACCGGATAAGACCCCTACCGCTTCGGCGGCAGAGGTAAAAGCTGACCTCTCCATGGAAGTTAGCGTTTGGGGACGGGCCCGCGTCCTATCAGCTTGTTGGTGGGGTAACAGCCCACCAAGGCAACGACGGGTAACTGGTCTGAGAGGATGATCAGTCACACTGGAACTGGAACACGGTCCAGACTCCTACGGGAGGCAGCAGTGAGGAATTTTGCGCAATGGGCGAAAGCCTGACGCAGCAACGCCGCGTGGGTGAAGAAGGCTTTCGGGTCGTAAAGCCCTGTCAGGTGGGAAGAAACCTTTCCGGTACTAATAATGCCGGAAATTGACGGTACCACCAAAGGAAGCACCGGCCAACTCCGTGCCAGCAGCCGCGGTAATACGGAGGGTGCAAGCGTTGTTCGGAATTATGGGGCGTAAAGAGCGTGTGGGCGGTTAGGAAAGTCAGATGTGAAAGCCCTGGGCTCAACCCAGGAAGTGCATTTGAAACTGCCTAACTTGAGTACGGGAGAGGAAGGGGGAATTCCCGGTGTAGAGGTGAAATTCGTAGATATCGGGAGGAATACCGGTGGCGAAGGCGCCCTTCTGGACCGATACTGACGCTGAGACGCGAAAGCGTGGGGAGCAAACAGGATTAGATACCCTGGTAGTCCACGCCGTAAACGATGAGCACTAGGTGTAGCGGGTATTGACCCCTGCTGTGCCGTAGCTAACGCATTAAGTGCTCCGCCTGGGGATTACGGTCGCAAGACTAAAACTCAAAGGAATTGACGGGGGCCCGCACAAGCGGTGGAGCATGTGGTTTAATTCGACGCAACGCGAAGAACCTTACCTGGGCTTGACATCCCCGGACAGCCCTGGAAACAGGGTCTCCCACTTCGGTGGGCTGGGTGACAGGTGCTGCATGGCTGTCGTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGAGCGCAACCCCTGCCTTTAGTTGCCATCATTTAGCTGGGCACTCTAAAGGGACTGCCGGTGTTAAACCGGAGGAAGGTGGGGACGACGTCAAGTCCTCATGGCCTTTATGCCCAGGGCTACACACGTGCTACAATGGGCGGTACAAAGGGCAGCGACATCGTGAGGTGAAGCAAATCCCAAAAAACCGCTCTCAGTTCGGATCGGAGTCTGCAACTCGACTTCGTGAAGGTGGAATCACTAGTAATCGTGGATCAGCATGCCACGGTGAATACGTTCCCGGGCCTTGTACACACCGCCCGTCACACCACGAAAGTCTGCTGTACCAGAAGTCGCTGGGCTAACCCGCCCTAGGCGGGAGGTAGGCGCCTAAGGTACGGCCGGTAATTGGGGTGAAGTCGTAACAAGGTAACC",
                       ">CP002079",
                       "GCTGGCGGCGTGCCTAACACATGTAAGTCGAACGGGACTGGGGGCAACTCCAGTTCAGTGGCAGACGGGTGCGTAACACGTGAGCAACTTGTCCGACGGCGGGGGATAGCCGGCCCAACGGCCGGGTAATACCGCGTACGCTCGTTTAGGGACATCCCTGAATGAGGAAAGCCGTAAGGCACCGACGGAGAGGCTCGCGGCCTATCAGCTAGTTGGCGGGGTAACGGCCCACCAAGGCGACGACGGGTAGCTGGTCTGAGAGGATGGCCAGCCACATTGGGACTGAGACACGGCCCAGACTCCTACGGGAGGCAGCAGTGGGGAATCTTGCGCAATGGCCGCAAGGCTGACGCAGCGACGCCGCGTGTGGGATGACGGCCTTCGGGTTGTAAACCACTGTCGGGAGGAACGAATACTCGGCTAGTCCGAGGGTGACGGTACCTCCAAAGGAAGCACCGGCTAACTCCGTGCCAGCAGCCGCGGTAATACGGAGGGTGCGAGCGTTGTCCGGAATCACTGGGCGTAAAGGGCGCGTAGGTGGCCCGTTAAGTGGCTGGTGAAATCCCGGGGCTCAACTCCGGGGCTGCCGGTCAGACTGGCGAGCTAGAGCACGGTAGGGGCAGATGGAATTCCCGGTGTAGCGGTGGAATGCGTAGATATCGGGAAGAATACCAGTGGCGAAGGCGTTCTGCTGGGCCGTTGCTGACACTGAGGCGCGACAGCGTGGGGAGCAAACAGGATTAGATACCCTGGTAGTCCACGCCGTAAACGATGGACACTAGACGTCGGGGGGAGCGACCCTCCCGGTGTCGTCGCTAACGCAGTAAGTGTCCCGCCTGGGGAGTACGGCCGCAAGGCTGAAACTCAAAGGAATTGACGGGGGCCCGCACAAGCGGTGGAGCATGTGGTTTAATTCGAAGCAACGCGAAGAACCTTACCTGGGCTTGACATGCTGGTGCAAGCCGGTGGAAACATCGGCCCCTCTTCGGAGCGCCAGCACAGGTGCTGCATGGCTGTCGTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGAGCGCAACTCTCGCTCCCAGTTGCCAGCGGTTCGGCCGGGGACTCTGGGGGGACTGCCGGCGTTAAGCCGGAGGAAGGTGGGGACGACGTCAAGTCATCATGGCCCTTACGTCCAGGGCGACACACGTGCTACAATGCCTGGTACAGCGCGTCGCGAACTCGCAAGAGGGAGCCAATCGCCAAAAGCCGGGCTAAGTTCGGATTGTCGTCTGCAACTCGACGGCATGAAGCCGGAATCGCTAGTAATCGCGGATCAGCCACGCCGCGGTGAATACGTTCCCGGGCCTTGTACACACCGCCCGTCACGCCATGGAAGCCGGAGGGACCCGAAACCGGTGGGCCAACCGCAAGGGGGCAGCCGTCTAAGGT",
                       ">CP002089",
                       "AGAGTTTGATCATGGCTCAGGATGAACGCTAGCGGCAGGCCTAACACATGCAAGTCGAGGGGTAGAGGCTTTCGGGCCTTGAGACCGGCGCACGGGTGCGTAACGCGTATGCAATCTGCCTTGTACTAAGGGATAGCCCAGAGAAATTTGGATTAATACCTTATAGTATATAGATGTGGCATCACATTTCTATTAAAGATTTATCGGTACAAGATGAGCATGCGTCCCATTAGCTAGTTGGTATGGTAACGGCATACCAAGGCAATGATGGGTAGGGGTCCTGAGAGGGAGATCCCCCACACTGGTACTGAGACACGGACCAGACTCCTACGGGAGGCAGCAGTGAGGAATATTGGTCAATGGGCGCAAGCCTGAACCAGCCATGCCGCGTGCAGGATGACGGTCCTATGGATTGTAAACTGCTTTTGTACGGGAAGAAACACTCCTACGTGTAGGGGCTTGACGGTACCGTAAGAATAAGGATCGGCTAACTCCGTGCCAGCAGCCGCGGTAATACGGAGGATCCAAGCGTTATCCGGAATCATTGGGTTTAAAGGGTCCGTAGGCGGTTTTATAAGTCAGTGGTGAAATCCGGCAGCTCAACTGTCGAACTGCCATTGATACTGTAGAACTTGAATTACTGTGAAGTAACTAGAATATGTAGTGTAGCGGTGAAATGCTTAGATATTACATGGAATACCAATTGCGAAGGCAGGTTACTAACAGTATATTGACGCTGATGGACGAAAGCGTGGGGAGCGAACAGGATTAGATACCCTGGTAGTCCACGCCGTAAACGATGGATACTAGCTGTTTGGCAGCAATGCTGAGTGGCTAAGCGAAAGTGTTAAGTATCCCACCTGGGGAGTACGAACGCAAGTTTGAAACTCAAAGGAATTGACGGGGGCCCGCACAAGCGGTGGAGCATGTGGTTTAATTCGATGATACGCGAGGAACCTTACCAGGGCTTAAATGTAGAGTGACAGGACTGGAAACAGTTTTTTCTTCGGACACTTTACAAGGTGCTGCATGGTTGTCGTCAGCTCGTGCCGTGAGGTGTCAGGTTAAGTCCTATAACGAGCGCAACCCCTGTTGTTAGTTGCCAGCGAGTAATGTCGGGAACTCTAACAAGACTGCCGGTGCAAACCGTGAGGAAGGTGGGGATGACGTCAAATCATCACGGCCCTTACGTCCTGGGCTACACACGTGCTACAATGGCCGGTACAGAGAGCAGCCACCTCGCGAGGGGGAGCGAATCTATAAAGCCGGTCACAGTTCGGATTGGAGTCTGCAACCCGACTCCATGAAGCTGGAATCGCTAGTAATCGGATATCAGCCATGATCCGGTGAATACGTTCCCGGGCCTTGTACACACCGCCCGTCAAGCCATGGAAGCTGGGGGTACCTGAAGTCGGTGACCGCAAGGAGCTGCCTAGGGTAAAACTGGTAACTGGGGCTAAGTCGTACAAGGTAGCCGTA",
                       ">CP002987",
                       "CCTAATGCATGCAAGTCGAACGCAGCAGGCGTGCCTGGCTGCGTGGCGAACGGCTGACGAACACGTGGGTGACCTGCCCCGGAGTGGGGGATACCCCGTCGAAAGACGGGACAATCACGCATACGCTCTTTGGAGGAAAGCCATCCGGCGCTCTGGGAGGGGCCTGCGGCCCATCAGGTAGTTGGTGTGGTAACGGCGCACCAAGCCAATGACGGGTACCCGGTCTGAGAGGACGACCGGCCAGACTGGAACTGCGACACGGCCCAGACTCCTACGGGAGGCAGCAGCAAGGAATTTTCCCCAATGGGCGCAAGCCTGAGGCAGCAACGCCGCGTGCGGGATGACGGACTTCGGGTTGTAAACCGCTTTTCGGGGGGACAACCCTGACGGTACCCCCGGAACAAGCCCCGGCTAACTCTGTGCCAGCAGCCGCGGTAAGACAGAGGGGGCAAGCGTTGTCCGGAGTCACTGGGCGTAAAGCGCGCGCAGGCGGCTGCCTAAGTGTCGTGTGAAAGCCCCCGGCTCAACCGGGGGAGGCCATGGCAAACTGGGTGGCTCGAGCGGCGGAGAGGTCCCTCGAATTGCCGGTGTAGCGGTGAAATGCGTAGAGATCGGCAGGAAGACCAAGGGGGAAGCCAGGGGGCTGGCCGCCGGCTGACGCTGAGGCGCGACAGCGTGGGGAGCAAACCGGATTAGATACCCGGGTAGTCCACGCCGTAAACGATGACCACTCGGCGTGTGGCGACTATTAACGTCGCGGCGCGCCCTAGCTCACGCGATAAGTGGTCCGCCTGGGAACTACGAGCGCAAGCTTAAAACTCAAAGGAATTGACGGGGGCCCGCACAAGCAGCGGAGCGTGTGGTTTAATTCGACGCAACCCGCAGAACCTTACCCAGACTGGACATGACGGTGCAGACGGCGGAAACGTCGTCGCCTGCGAGGGTCCGTCACAGGTGCTGCATGGCTGTCGTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGAGCGCAACCCCTGCGGTTAGTTACCCGTGTCTAACCGGACTGCCCTTCGGGGAGGAAGGCGGGGATGACGTCAAGTCCGCATGGCCCTTACGTCTGGGGCGACACACACGCTACAATGGCGCCGACAATGCGTCGCTCCCGCGCAAGCGGATGCTAATCGCCAAACGGCGCCCCAGTGCAGATCGGGGGCTGCAACTCGCCCCCGTGAAGGCGGAGTTGCTAGTAACCGCGTATCAGCCATGGCGCGGTGAATACGTACCCGGGCCTTGTACACACCGCCCGTCACGTCATGGAGTTGTCAATGCCTGAAGTCCGCCAGCTAACC"
                       ]
            open(self.rrnaFile,'w').write('\n'.join(rrnas))
            operons = [ "CP002059.1_4|regulator.fa.cluster2.fa|6.3e-45|31|182|1453672|1453887|'Nostoc azollae' 0708, complete genome",
                        "CP002059.1_4|regulator.fa.cluster2.fa|6.3e-45|2|106|1452256|1452392|'Nostoc azollae' 0708, complete genome ",
                        "CP002059.1_2|regulator.fa.cluster2.fa|3.7e-79|1|222|1444330|1444547|'Nostoc azollae' 0708, complete genome ",
                        "CP002059.1_3|regulator.fa.cluster2.fa|3.2e-43|2|115|1434009|1434139|'Nostoc azollae' 0708, complete genome ",
                        "CP002059.1_2|regulator.fa.cluster2.fa|3.7e-79|1|121|1433807|1433960|'Nostoc azollae' 0708, complete genome ",
                        "CP002059.1_2|regulator.fa.cluster2.fa|3.7e-79|1|222|1433433|1433650|'Nostoc azollae' 0708, complete genome ",
                        "CP002059.1_2|toxin.fa.cluster9.fa|1.7e-22|14|116|1418714|1418849|'Nostoc azollae' 0708, complete genome	",
                        "CP002059.1_6|modifier.fa.cluster16.fa|6.4e-21|4|245|1405183|1405432|'Nostoc azollae' 0708, complete genome ",
                        "CP002059.1_4|immunity.fa.cluster5.fa|3.8e-49|1|139|1414069|1414207|'Nostoc azollae' 0708, complete genome  ",
                        "CP002059.1_6|transport.fa.cluster4.fa|4.4e-98|30|173|1405726|1405974|'Nostoc azollae' 0708, complete genome",
                        "----------",
                        "CP002059.1_1|immunity.fa.cluster2.fa|7.2e-109|121|184|1648008|1648106|'Nostoc azollae' 0708, complete genome",
                        "CP002059.1_1|transport.fa.cluster12.fa|4.7e-159|17|48|1647817|1647862|'Nostoc azollae' 0708, complete genome",
                        "CP002059.1_1|transport.fa.cluster4.fa|1.1e-47|90|203|1647624|1647771|'Nostoc azollae' 0708, complete genome",
                        "CP002059.1_5|toxin.fa.cluster109.fa|2e-46|15|134|1683374|1683516|'Nostoc azollae' 0708, complete genome	",
                        "CP002059.1_5|regulator.fa.cluster2.fa|3e-154|2|222|1653489|1653706|'Nostoc azollae' 0708, complete genome  ",
                        "CP002059.1_4|modifier.fa.cluster14.fa|6.8e-12|15|123|1670650|1670829|'Nostoc azollae' 0708, complete genome",
                        "CP002059.1_1|transport.fa.cluster4.fa|1.1e-47|11|62|1672798|1672908|'Nostoc azollae' 0708, complete genome ",
                        "----------",
                        "CP002059.1_3|regulator.fa.cluster2.fa|3.2e-43|2|115|1434009|1434139|'Nostoc azollae' 0708, complete genome ",
                        "CP002059.1_2|regulator.fa.cluster2.fa|3.7e-79|1|121|1433807|1433960|'Nostoc azollae' 0708, complete genome ",
                        "CP002059.1_2|regulator.fa.cluster2.fa|3.7e-79|1|222|1433433|1433650|'Nostoc azollae' 0708, complete genome ",
                        "CP002059.1_2|regulator.fa.cluster2.fa|3.7e-79|39|140|1388016|1388161|'Nostoc azollae' 0708, complete genome",
                        "CP002059.1_2|toxin.fa.cluster9.fa|1.7e-22|14|116|1418714|1418849|'Nostoc azollae' 0708, complete genome	",
                        "CP002059.1_6|modifier.fa.cluster16.fa|6.4e-21|4|245|1405183|1405432|'Nostoc azollae' 0708, complete genome ",
                        "CP002059.1_4|immunity.fa.cluster5.fa|3.8e-49|1|139|1414069|1414207|'Nostoc azollae' 0708, complete genome  ",
                        "CP002059.1_6|transport.fa.cluster4.fa|4.4e-98|30|173|1405726|1405974|'Nostoc azollae' 0708, complete genome",
                        "----------",
                        "CP002987.1_6|transport.fa.cluster4.fa|9.7e-249|23|211|455701|455990|Acetobacterium woodii DSM 1030, complete genome",
                        "CP002987.1_4|transport.fa.cluster4.fa|1.2e-123|31|212|444740|445012|Acetobacterium woodii DSM 1030, complete genome",
                        "CP002987.1_6|transport.fa.cluster4.fa|9.7e-249|8|209|455197|455450|Acetobacterium woodii DSM 1030, complete genome ",
                        "CP002987.1_3|toxin.fa.cluster109.fa|8.7e-26|31|145|441072|441212|Acetobacterium woodii DSM 1030, complete genome   ",
                        "CP002987.1_1|transport.fa.cluster4.fa|3.1e-155|28|176|461075|461388|Acetobacterium woodii DSM 1030, complete genome",
                        "CP002987.1_2|transport.fa.cluster14.fa|1.2e-193|7|106|461954|462062|Acetobacterium woodii DSM 1030, complete genome",
                        "CP002987.1_2|transport.fa.cluster13.fa|1.8e-88|6|70|461822|461931|Acetobacterium woodii DSM 1030, complete genome  ",
                        "CP002987.1_3|immunity.fa.cluster5.fa|1.7e-50|1|139|417714|417852|Acetobacterium woodii DSM 1030, complete genome   ",
                        "CP002987.1_4|modifier.fa.cluster15.fa|1.1e-14|3|190|436172|436362|Acetobacterium woodii DSM 1030, complete genome  ",
                        "CP002987.1_6|regulator.fa.cluster2.fa|1.7e-108|35|117|424891|425106|Acetobacterium woodii DSM 1030, complete genome",
                        "CP002987.1_1|regulator.fa.cluster4.fa|0.44|5|43|425111|425160|Acetobacterium woodii DSM 1030, complete genome  	",
                        "CP002987.1_5|transport.fa.cluster4.fa|2.8e-272|13|234|424279|424569|Acetobacterium woodii DSM 1030, complete genome",
                        "CP002987.1_5|modifier.fa.cluster16.fa|5.5e-42|2|245|435804|436053|Acetobacterium woodii DSM 1030, complete genome  ",
                        "CP002987.1_5|modifier.fa.cluster10.fa|2.4e-06|7|183|429873|430075|Acetobacterium woodii DSM 1030, complete genome  ",
                        "----------"]
            open(self.operonFile,'w').write('\n'.join(operons))
            self.itol = None
            
        def tearDown(self):
            os.remove(self.rrnaFile)
            os.remove(self.operonFile)
            #if not self.itol==None:
            #    self.itol.cleanUp()
        def testGetRRNAS(self):
            self.itol = iTOL(self.operonFile,self.rrnaFile)
            self.itol.getRRNAs()
            self.assertTrue(os.path.getsize(self.itol.rrnaFile)>0)
            seq_records = list(SeqIO.parse(open(self.itol.rrnaFile,'r'), "fasta"))
            self.assertEquals(len(seq_records),2)
        def testBuildTree(self):
            self.itol = iTOL(self.operonFile,self.rrnaFile)
            self.itol.getRRNAs()
            self.itol.buildTree()
            self.assertTrue(os.path.getsize(self.itol.treeFile)>0)
            
            
    unittest.main()
    
    
    