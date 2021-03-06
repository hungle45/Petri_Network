from string import Template
import time
import keyboard
import sys
import msvcrt

class Place:
    def __init__(self, token:int = 0, label:str = 'p'):
        self.token = max(token,0)
        self.label = label

    def non_blocking(self)->bool:
        return self.token >= 1

    def trigger(self, state:bool):
        '''
        state = true: place send token to transion
        state = false: place get token from transition
        '''
        if self.token <= 0 and state: return
        self.token -= 1 if state else -1

    def __str__(self):
        log = 'Place \'{}\': {} token'.format(self.label,self.token)
        if self.token >= 2:
            log += 's'
        return log
    
    @classmethod
    def create_n(cls, size, marking:list=[]):
        if size <= 0: return
        if size > len(marking):
            marking += [0]*(size-len(marking))
        labels = ['p{}'.format(i) for i in range(size)]
        ps = []
        for i in range(size):
            ps.append(cls(marking[i],labels[i]))
        return ps


class Transition:
    def __init__(self, label:str = 't'):
        self.__preset = []
        self.__postset = []
        self.label = label

    def add_preset(self,place):
        self.__preset.append(place)

    def add_postset(self,place):
        self.__postset.append(place)

    def is_enable(self):
        return all([p.non_blocking() for p in self.__preset])

    def fire(self):
        flag = self.is_enable()
        if self.is_enable():
            for p in self.__preset:
                p.trigger(True)
            for p in self.__postset:
                p.trigger(False)
        return flag

    def __str__(self):
        return 'Transision \'{}\': {} in, {} out'.format(
            self.label, len(self.__preset), len(self.__postset)
        )
    
    @classmethod
    def create_with_set(cls, preset:list, postset:list, label:str = ''):
        t = cls(label)
        for p in preset:
            t.add_preset(p)
        for p in postset:
            t.add_postset(p)
        return t


class PetriNetwork:
    def __init__(self, transitions:dict, marking:list):
        self.P = Place.create_n(len(marking),marking)
        self.T = []
        for key,val in transitions.items():
            preset = [self.P[i] for i in val[0]]
            postset = [self.P[i] for i in val[1]]
            t = Transition.create_with_set(preset, postset, key)
            self.T.append(t)

    def add_P_label(self, labels:list):
        if len(labels) != len(self.P):
            print('Labels length not match')
            return
        for p,l in zip(self.P,labels):
            p.label = l

    def add_T_label(self, labels:list):
        if len(labels) != len(self.T):
            print('Labels length not match')
            return
        for t,l in zip(self.T,labels):
            t.label = l

    def set_marking(self, marking:list):
        if len(marking) != len(self.P):
            return False
        for p,m in zip(self.P,marking):
            p.token = m
        return True

    def reachable_marking(self, filename:str = 'reachable_marking.txt'):
        f = open(filename,'w')
        templ_str = Template('Firing sequence: $fs\nMarking: $m\n\n')
        init_mark = tuple([p.token for p in self.P])
        marking_set = set()
        marking_set.add(init_mark)
        queue = [[[],init_mark]]
        count = 0

        while len(queue) != 0:
            cur_seq,cur_mark = queue[0]
            queue.pop(0)
            self.set_marking(cur_mark)
            f.write(templ_str.substitute(fs=cur_seq,m=self.marking))
            count+=1
            for t in self.T:
                if t.is_enable():
                    t.fire()
                    m = tuple([p.token for p in self.P])
                    if m not in marking_set:
                        marking_set.add(m)
                        queue.append([cur_seq+[t.label], m])
                    self.set_marking(cur_mark)

        print('There are {} reachable marking'.format(count))
        print('Open file \'{}\' to view all'.format(filename))
        self.set_marking(init_mark)

    def auto_firing(self):
            templ_str = Template('\'$t\' fired!\nMarking: $m\n')
            is_deadblock = False
            print('Start {}\n'.format(self.marking))

            while not is_deadblock:
                is_deadblock = True
                for t in self.T:
                    if t.is_enable():
                        t.fire()
                        is_deadblock = False
                        print(templ_str.substitute(t=t.label, m=self.marking))
                        for i in range(20):
                            if keyboard.is_pressed('p'):
                                print('Continue (Y/N)?')
                                while True:
                                    if keyboard.is_pressed('y'):
                                        break
                                    if keyboard.is_pressed('n'):
                                        return
                                break
                            else:
                                time.sleep(0.05)
                        break
            if is_deadblock:
                print('Deadblock!')
            else:
                print('To be continued...')
            
    def __str__(self):
        ps = [p.label for p in self.P]
        ts = [t.label for t in self.T]
        m = self.marking
        return 'P = {}\nT = {}\nM = {}'.format(ps,ts,m)

    @property
    def marking(self):
        marking = '['
        for p in self.P:
            marking += '{}.{}, '.format(p.token,p.label)
        marking = marking[:-2]+']'
        return marking

    def fire(self, t_index:int):
        if t_index >= len(self.T):
            print('Out of range transition')
            return
        if t_index < 0:
            print('Index must be non-negative')
            return
        t = self.T[t_index]
        t_label = t.label if t.label != 't' else 't{}'.format(t_index)
        if self.T[t_index].fire():
            print('\'{}\' fired!'.format(t_label))
            print('Current marking: {}'.format(self.marking))
        else:
            print('\'{}\' is not enabled'.format(t_label))
    
    def convert_to_TS(self, filename: str = 'transition_system.txt'):
        f = open(filename, 'w')
        templ_str = Template('S = {\n\t$fs\n}\nA = { $m }\nTR = {\n\t$n\n}\n')
        my_dict = {}
        rout = []
        S = []
        A = ' , '.join([t.label for t in self.T])
        init_mark = tuple([p.token for p in self.P])
        queue = [init_mark]
        marking_set = set()
        marking_set.add(init_mark)
        count = 1
        while len(queue) != 0:
            cur_mark = queue[0]
            queue.pop(0)
            self.set_marking(cur_mark)
            if self.marking not in my_dict:
                my_dict[self.marking] = count
                count += 1
            for t in self.T:
                if t.is_enable():
                    sign = ['S{}'.format(my_dict[self.marking]), t.label]
                    t.fire()
                    if self.marking not in my_dict:
                        my_dict[self.marking] = count
                        count += 1
                    sign.append('S{}'.format(my_dict[self.marking]))
                    m = tuple([p.token for p in self.P])
                    if m not in marking_set:
                        marking_set.add(m)
                        queue.append(m)
                    rout.append('[{}]'.format('->'.join(sign)))
                    self.set_marking(cur_mark)
        for key, Value in my_dict.items():
            S_unit = 'S{} = {}'.format(Value, key)
            S.append(S_unit)
        print('Open file \'{}\' to see the result'.format(filename))
        f.write('\tTRANSION SYSTEM\n')
        f.write('There are {} states, {} transitions\n'.format(len(S),len(rout)))
        f.write(templ_str.substitute(fs='\n\t'.join(S), m=A, n='\n\t'.join(rout)))

if __name__ == '__main__':
    # sample input
    marking = [1,0,0]
    transitions = {
        't1': [[0],[1]],
        't2': [[1],[2]]
    }
    t_labels = ['start','change']
    p_labels = ['wait','inside','done']

    net = PetriNetwork(transitions, marking)
    net.add_P_label(p_labels)
    net.add_T_label(t_labels)
    print(net.marking)