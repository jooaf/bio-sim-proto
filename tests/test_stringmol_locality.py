"""Directed synthetic reconstruction fixtures; no population executions."""
import pytest
from experiments.stringmol.locality_geometry import cells,candidates,vacancies,Boundary
from experiments.stringmol.configure_control import inoculum,HOST
from experiments.stringmol.analyze_conservation import initial_material


def test_explicit_log_controls_for_future_recovery():
    from experiments.stringmol.locality_pilot import locality_environment
    on,off=locality_environment(True),locality_environment(False)
    for key in ('STRINGMOL_CONSERVATION_LOG','STRINGMOL_SCHEDULING_LOG','STRINGMOL_RETIREMENT_LOG'):
        assert on[key]=='1' and off[key]=='0'
    assert on['STRINGMOL_LINEAGE_LOG']=='1' and 'STRINGMOL_LINEAGE_LOG' not in off
    assert {k:v for k,v in on.items() if not k.endswith('_LOG')}=={k:v for k,v in off.items() if not k.endswith('_LOG')}


def test_torus_and_order():
    assert cells((0,0),1) == [(39,39),(39,0),(39,1),(0,39),(0,0),(0,1),(1,39),(1,0),(1,1)]
    grid={0:(0,0),1:(39,39),2:(1,1),3:(20,20)}
    eligible=lambda _:0
    assert candidates([3,2,1],{},grid,0,0,0,eligible)==[3,2,1]
    assert candidates([3,2,1],{},grid,0,1,0,eligible)==[1,2]
    assert candidates([3,2,1],{1:4},grid,0,1,0,eligible)==[2]
    assert candidates([3,2,1],{},grid,0,1,0,lambda i: 1 if i==2 else 0)==[1]


def test_placement_and_reject():
    grid={0:(0,0),1:(20,20)}
    assert len(vacancies(grid,0,1))==8
    assert (39,39) in vacancies(grid,0,1)
    assert (20,19) not in vacancies(grid,0,1)
    full={i:c for i,c in enumerate(cells((0,0),1))}
    assert vacancies(full,4,1)==[]
    assert len(vacancies(full,4,0))==1591
    with pytest.raises(ValueError): cells((0,0),2)


def test_stream_exact_bytes_and_bounded_memory(tmp_path):
    import tracemalloc
    from experiments.stringmol.locality_replay import canonical_stream
    path=tmp_path/'stream.csv'
    path.write_bytes(b'a,b\n'+b'1,2\n'*10000)
    tracemalloc.start()
    assert sum(1 for _ in canonical_stream(path,['a','b']))==10000
    _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    assert peak < 1024*1024
    for raw in (b'a,b\n1,2',b'a,b\r\n1,2\n',b'a,b\n"1",2\n',b'a,b\n1,2,3\n'):
        path.write_bytes(raw)
        with pytest.raises(ValueError):list(canonical_stream(path,['a','b']))


def test_fixed_initial():
    host,_=inoculum()
    assert len(host)==140 and len(set(host))==140
    assert len(HOST)==64


def test_local_boundary_candidate_rank_tampering():
    # Synthetic valid SEARCH at a pre-established action boundary. Verify native
    # queue is preserved rather than left in geometric order.
    from experiments.stringmol.analyze_scheduling import DEFAULTS
    initial=initial_material([{'id':i,'sequence_hex':HOST.encode().hex()} for i in range(4)],'histogram',0)
    initial['waste']=[0]*33
    def fixture():
        b=Boundary(initial,[],'IMMEDIATE',grid={0:(0,0),1:(39,39),2:(1,1),3:(20,20)},interaction=1)
        b.started=True;b.tick=0;b.index=1;b.now=[3,2,1];b.selection=(0,-1);b.phase='action'
        return b
    row={**DEFAULTS,'event':'SEARCH','tick':'0','index':'2','policy':'IMMEDIATE','id':'0','other':'2','count':'2','selected':'1','outcome':'SELECTED'}
    b=fixture();b.step(row)
    assert b.now==[3,1] and b.search==(2,2,1)
    for field,value in [('other','3'),('count','3'),('selected','0')]:
        with pytest.raises(ValueError): fixture().step({**row,field:value})
