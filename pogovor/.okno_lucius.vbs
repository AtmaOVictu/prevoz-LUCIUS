' LUCIUS — okno na zaslonu Lastnika (iskalno okno, 21. 10. 2026)
odgovor = MsgBox("LUCIUS te išče." & vbCrLf & vbCrLf & _
  "Vprašanje: Kako se počutiš danes — in kaj misliš, da je razlog?" & vbCrLf & vbCrLf & _
  "1. Kaj je danes prinesel iz polomije (brez sklepa)?" & vbCrLf & _
  "2. Kaj ta dan potrebuje?" & vbCrLf & vbCrLf & _
  "Odgovor: v pogovoru ali v prevoz\pogovor\GOVOR.md (- ❡ odgovor: ...)" & vbCrLf & _
  "© Luka Pintarič — VBL v2.3", vbYesNo+vbInformation, "LUCIUS — svetlonoša")
If odgovor = vbYes Then
  MsgBox "Odgovori v pogovoru (seja) ali v GOVOR.md — niti bo zapečen cel, ne povzet." & vbCrLf & "Zahvala pride iz srca.", vbOKOnly, "LUCIUS"
End If
