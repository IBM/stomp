#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gantt
import datetime
import os
import logging

from nose.tools import assert_equals
from nose import with_setup


def setup():
    gantt.init_log_to_sysout(level=logging.CRITICAL)
    return


#def test_flatten():
#    assert_equals(gantt._flatten([1, [2, 3], [[4, 5], 6]]), [1, 2, 3, 4, 5, 6])
#    return


def test_add_vacations_1():
    gantt.add_vacations(datetime.date(2015, 1, 1))
    gantt.add_vacations(datetime.date(2014, 12, 25))
    # test global vacations
    assert_equals(gantt.VACATIONS, [datetime.date(2015, 1, 1), datetime.date(2014, 12, 25)])
    return


def test_add_vacations_2():
    gantt.add_vacations(datetime.date(2013, 12, 25), datetime.date(2013, 12, 27))
    # test global vacations
    assert datetime.date(2013, 12, 25) in gantt.VACATIONS
    assert datetime.date(2013, 12, 26) in gantt.VACATIONS
    assert datetime.date(2013, 12, 27) in gantt.VACATIONS
    assert datetime.date(2013, 12, 28) not in gantt.VACATIONS
    assert datetime.date(2013, 12, 24) not in gantt.VACATIONS
    return


def test_Resources():
    rANO = gantt.Resource('ANO')
    rANO.add_vacations(
        dfrom=datetime.date(2015, 2, 2), 
        dto=datetime.date(2015, 2, 4) 
        )
    # test global vacations
    assert_equals(rANO.is_available(datetime.date(2015, 1, 1)), False)
    # test resource vacations
    assert_equals(rANO.is_available(datetime.date(2015, 2, 1)), True)
    assert_equals(rANO.is_available(datetime.date(2015, 2, 2)), False)
    assert_equals(rANO.is_available(datetime.date(2015, 2, 3)), False)
    assert_equals(rANO.is_available(datetime.date(2015, 2, 3)), False)
    assert_equals(rANO.is_available(datetime.date(2015, 2, 5)), True)

    # Second resource
    rJLS = gantt.Resource('JLS')
    return
    

def test_Tasks():
    tSADU = gantt.Task(name='tache SADU', start=datetime.date(2014, 12, 25), duration=4)
    assert_equals((tSADU.start_date(), tSADU.end_date()), (datetime.date(2014, 12, 26), datetime.date(2014, 12, 31)))
    assert_equals(tSADU.nb_elements(), 1)
 
    tSAST = gantt.Task(name='tache SAST', start=datetime.date(2014, 12, 25), stop=datetime.date(2014, 12, 31))
    assert_equals((tSAST.start_date(), tSAST.end_date()), (datetime.date(2014, 12, 26), datetime.date(2014, 12, 31)))

    tDUST = gantt.Task(name='tache DUST', stop=datetime.date(2014, 12, 31), duration=4)
    assert_equals((tDUST.start_date(), tDUST.end_date()), (datetime.date(2014, 12, 26), datetime.date(2014, 12, 31)))

    tDUSTSADU = gantt.Task(name='tache DUST SADU', start=datetime.date(2015, 1, 1), duration=4, depends_of=[tDUST])
    assert_equals((tDUSTSADU.start_date(), tDUSTSADU.end_date()), (datetime.date(2015, 1, 2), datetime.date(2015, 1, 7)))

    tDUSTSAST = gantt.Task(name='tache DUST SAST', start=datetime.date(2015, 1, 1), stop=datetime.date(2015, 1, 7), depends_of=[tDUST])
    assert_equals((tDUSTSAST.start_date(), tDUSTSAST.end_date()), (datetime.date(2015, 1, 2), datetime.date(2015, 1, 7)))

    tDUSTDUST = gantt.Task(name='tache DUST DUST', stop=datetime.date(2015, 1, 7), duration=9, depends_of=[tDUST])
    assert_equals((tDUSTDUST.start_date(), tDUSTDUST.end_date()), (datetime.date(2015, 1, 2), datetime.date(2015, 1, 7)))

    tDUSTDUST2 = gantt.Task(name='tache DUST DUST2', stop=datetime.date(2015, 1, 10), duration=2, depends_of=[tDUST])
    assert_equals((tDUSTDUST2.start_date(), tDUSTDUST2.end_date()), (datetime.date(2015, 1, 8), datetime.date(2015, 1, 9)))


    tSADUSADU = gantt.Task(name='tache SADU SADU', start=datetime.date(2015, 1, 1), duration=4, depends_of=[tSADU])
    assert_equals((tSADUSADU.start_date(), tSADUSADU.end_date()), (datetime.date(2015, 1, 2), datetime.date(2015, 1, 7)))

    tSADUSAST = gantt.Task(name='tache SADU SAST', start=datetime.date(2015, 1, 1), stop=datetime.date(2015, 1, 7), depends_of=[tSADU])
    assert_equals((tSADUSAST.start_date(), tSADUSAST.end_date()), (datetime.date(2015, 1, 2), datetime.date(2015, 1, 7)))

    tSADUDUST = gantt.Task(name='tache SADU DUST', stop=datetime.date(2015, 1, 7), duration=9, depends_of=[tSADU])
    assert_equals((tSADUDUST.start_date(), tSADUDUST.end_date()), (datetime.date(2015, 1, 2), datetime.date(2015, 1, 7)))

    tSADUDUST2 = gantt.Task(name='tache SADU DUST2', stop=datetime.date(2015, 1, 10), duration=2, depends_of=[tSADU])
    assert_equals((tSADUDUST2.start_date(), tSADUDUST2.end_date()), (datetime.date(2015, 1, 8), datetime.date(2015, 1, 9)))



    tSASTSADU = gantt.Task(name='tache SAST SADU', start=datetime.date(2015, 1, 1), duration=4, depends_of=[tSAST])
    assert_equals((tSASTSADU.start_date(), tSASTSADU.end_date()), (datetime.date(2015, 1, 2), datetime.date(2015, 1, 7)))

    tSASTSAST = gantt.Task(name='tache SAST SAST', start=datetime.date(2015, 1, 1), stop=datetime.date(2015, 1, 7), depends_of=[tSAST])
    assert_equals((tSASTSAST.start_date(), tSASTSAST.end_date()), (datetime.date(2015, 1, 2), datetime.date(2015, 1, 7)))

    tSASTDUST = gantt.Task(name='tache SAST DUST', stop=datetime.date(2015, 1, 7), duration=9, depends_of=[tSAST])
    assert_equals((tSASTDUST.start_date(), tSASTDUST.end_date()), (datetime.date(2015, 1, 2), datetime.date(2015, 1, 7)))

    tSASTDUST2 = gantt.Task(name='tache SAST DUST2', stop=datetime.date(2015, 1, 10), duration=2, depends_of=[tSAST])
    assert_equals((tSASTDUST2.start_date(), tSASTDUST2.end_date()), (datetime.date(2015, 1, 8), datetime.date(2015, 1, 9)))


    tBUG = gantt.Task(name='tBUG', start=datetime.date(2015, 1, 9), duration=7)
    assert_equals((tBUG.start_date(), tBUG.end_date()), (datetime.date(2015, 1, 9), datetime.date(2015, 1, 19)))

    tBUG2 = gantt.Task(name='tBUG2', start=datetime.date(2015, 1, 10), duration=7)
    assert_equals((tBUG2.start_date(), tBUG2.end_date()), (datetime.date(2015, 1, 12), datetime.date(2015, 1, 20)))

    tBUG3 = gantt.Task(name='tBUG3-,\'/()', start=datetime.date(2015, 1, 10), duration=7)

    
    p1 = gantt.Project(name='Projet 1')

    assert_equals(p1.nb_elements(), 0)

    p1.add_task(tSADU)
    p1.add_task(tSAST)
    p1.add_task(tDUST)
    p1.add_task(tDUSTSADU)
    p1.add_task(tDUSTSAST)
    p1.add_task(tDUSTDUST)
    p1.add_task(tDUSTDUST2)

    p1.add_task(tSADUSADU)
    p1.add_task(tSADUSAST)
    p1.add_task(tSADUDUST)
    p1.add_task(tSADUDUST2)
    
    p1.add_task(tSASTSADU)
    p1.add_task(tSASTSAST)
    p1.add_task(tSASTDUST)
    p1.add_task(tSASTDUST2)

    assert_equals(p1.is_in_project(tBUG), False)
    
    p1.add_task(tBUG)

    assert_equals(p1.is_in_project(tBUG), True)

    p1.add_task(tBUG2)
    p1.add_task(tBUG3)

    assert_equals(p1.nb_elements(), 18)

    assert_equals(p1.start_date(), datetime.date(2014, 12, 26))
    assert_equals(p1.end_date(), datetime.date(2015, 1, 20))


    p1.make_svg_for_tasks(filename='./h.svg', today=datetime.date(2014, 12, 31))
    assert os.path.isfile('./h.svg')


    assert_equals(p1.get_resources(), [])
    assert_equals(len(p1.get_tasks()), 18)
    return
    
