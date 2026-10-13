"""Never harden, hide, or quit a non-owned WPS session."""
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
import win32com.client
from wps_cli.backends.wps_com import WpsComBackend, ForeignWpsSessionError


@pytest.mark.parametrize('component,collection', [('writer','Documents'),('calc','Workbooks'),('impress','Presentations')])
@pytest.mark.parametrize('count,visible', [(1,False),(0,True)])
def test_foreign_session_rejected_before_mutation(monkeypatch,component,collection,count,visible):
    app=SimpleNamespace(Version='12.1',Visible=visible,Quit=MagicMock())
    setattr(app,collection,SimpleNamespace(Count=count))
    dispatch=MagicMock(return_value=app)
    monkeypatch.setattr(win32com.client,'DispatchEx',dispatch)
    backend=WpsComBackend()
    backend.harden=MagicMock()
    with pytest.raises(ForeignWpsSessionError,match='WPS_FOREIGN_SESSION'):
        backend.connect(component)
    assert dispatch.call_count==1
    backend.harden.assert_not_called()
    app.Quit.assert_not_called()
    assert app.Visible==visible


@pytest.mark.parametrize('component,collection', [('writer','Documents'),('calc','Workbooks'),('impress','Presentations')])
def test_empty_hidden_session_admitted(monkeypatch,component,collection):
    app=SimpleNamespace(Version='12.1',Visible=False)
    setattr(app,collection,SimpleNamespace(Count=0))
    monkeypatch.setattr(win32com.client,'DispatchEx',lambda _:app)
    backend=WpsComBackend()
    backend.harden=MagicMock()
    assert backend.connect(component) is app
    backend.harden.assert_called_once_with(app)
