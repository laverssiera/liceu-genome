#!/usr/bin/env python3
"""Mutacoes da regra de data — e a superficie que a prova dela cobre.

Dez exercitam a funcao pura, dois sao CONTROLE POSITIVO (data de hoje e de
ontem passam) e quatro provam a LIGACAO: que o juiz de fato chama esta regra,
que a forma e recusada pela LEI antes do juiz, que o 'hoje' vem de `hoje_utc()`
e nao do fuso local, e que o grafo real passa limpo.

Sem o controle positivo, uma guarda que recusasse TODA data passaria em todos
os casos de recusa. Sem os de ligacao, mover a regra para um modulo proprio
criaria o risco obvio: uma regra perfeita que ninguem invoca.
"""
import datetime
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import genome_check as gc  # noqa: E402
import genome_date_check as gdc  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HOJE = "2026-10-01"
AMANHA = "2026-10-02"


def achados(**nos) -> list[str]:
    """Os achados da regra, com o 'hoje' DECLARADO — um teste de data que
    dependesse do relogio passaria no dia em que foi escrito e apodreceria no
    dia seguinte."""
    return gdc.achados(nos, HOJE)


class Recusas(unittest.TestCase):
    def test_prova_datada_de_amanha(self):
        a = achados(proof=[{"id": "PRF-X", "date": AMANHA}])
        self.assertTrue(any("depois de hoje" in x for x in a), a)

    def test_data_de_hoje_passa(self):
        """CONTROLE POSITIVO. Sem ele, `>` trocado por `>=` — ou qualquer recusa
        cega — passaria em todos os casos acima e abaixo."""
        self.assertEqual(achados(proof=[{"id": "PRF-X", "date": HOJE}]), [])

    def test_data_de_ontem_passa(self):
        self.assertEqual(achados(proof=[{"id": "PRF-X", "date": "2026-09-30"}]), [])

    def test_data_que_nao_existe_no_calendario(self):
        a = achados(proof=[{"id": "PRF-X", "date": "2026-02-30"}])
        self.assertTrue(any("nao existe no calendario" in x for x in a), a)

    def test_forma_sem_zero_a_esquerda(self):
        """Em texto, 2026-9-30 e MAIOR que 2026-09-30; no calendario, MENOR.
        Como toda comparacao do juiz e de texto, a forma errada inverteria o
        veredito em silencio."""
        self.assertLess("2026-09-30", "2026-9-30")            # a inversao, medida
        self.assertIn("nao esta em YYYY-MM-DD", gdc.data_invalida("2026-9-30"))
        self.assertIsNone(gdc.data_invalida("2026-09-30"))

    def test_data_sem_aspas_vira_objeto_e_e_recusada(self):
        """Sem aspas, o YAML converte a data em datetime.date, e dai a
        comparacao com string levanta TypeError em vez de dar veredito."""
        self.assertIn("nao e texto", gdc.data_invalida(datetime.date(2026, 10, 1)))

    def test_pfc_datado_do_futuro(self):
        a = achados(pfc=[{"id": "FC-X", "date": AMANHA}])
        self.assertTrue(any("depois de hoje" in x for x in a), a)

    def test_pre_registro_no_futuro(self):
        """Previsao registrada amanha nao pre-registra nada: a FIT-016 pergunta
        se a prova veio DEPOIS do registro, e o futuro ali afrouxa a regra."""
        a = achados(claim=[{"id": "CLM-X", "prediction": {"registered_at": AMANHA}}])
        self.assertTrue(any("registered_at" in x for x in a), a)

    def test_pre_registro_mal_formado(self):
        a = achados(claim=[{"id": "CLM-X", "prediction": {"registered_at": "22/09/2026"}}])
        self.assertTrue(any("registered_at" in x for x in a), a)


class OFuturoQueELegitimo(unittest.TestCase):
    """`expires_at` diz quando a evidencia VENCE. Uma guarda que recusasse data
    futura sem distinguir campo quebraria o STALE inteiro — e o STALE e o que
    separa 'precisa ser provado de novo' de 'e falso'."""

    def test_expires_at_no_futuro_passa(self):
        self.assertEqual(achados(proof=[{"id": "PRF-X", "date": HOJE,
                                         "expires_at": "2027-01-01"}]), [])

    def test_expires_at_mal_formado_e_recusado(self):
        a = achados(proof=[{"id": "PRF-X", "date": HOJE, "expires_at": "01/01/2027"}])
        self.assertTrue(any("expires_at" in x for x in a), a)


class OFuso(unittest.TestCase):
    def test_hoje_utc_e_a_data_utc(self):
        self.assertEqual(gdc.hoje_utc(),
                         datetime.datetime.now(datetime.timezone.utc).date().isoformat())

    def test_a_data_local_pode_divergir_da_utc(self):
        """O defeito nao e hipotetico: em 2026-09-30 as 23h26 em UTC-3,
        `date.today()` dizia 2026-09-30 e a CI, em UTC, ja estava em 2026-10-01.
        O mesmo grafo receberia dois vereditos."""
        tarde = datetime.datetime(2026, 9, 30, 23, 26,
                                  tzinfo=datetime.timezone(datetime.timedelta(hours=-3)))
        self.assertEqual(tarde.date().isoformat(), "2026-09-30")
        self.assertEqual(tarde.astimezone(datetime.timezone.utc).date().isoformat(),
                         "2026-10-01")


class Ligacao(unittest.TestCase):
    """O juiz chama a regra? E com que 'hoje'?"""

    SCHEMA = json.loads((ROOT / "schema" / "genome.schema.json").read_text(encoding="utf-8"))

    def julgar(self, mutacao=None, today=None):
        d = Path(tempfile.mkdtemp())
        try:
            for f in sorted((ROOT / "genome").glob("*.yaml")):
                nos = yaml.safe_load(f.read_text(encoding="utf-8")) or []
                if mutacao:
                    for n in nos:
                        if n.get("id") == mutacao[0]:
                            n[mutacao[1]] = mutacao[2]
                (d / f.name).write_text(
                    yaml.safe_dump(nos, allow_unicode=True, sort_keys=False), encoding="utf-8")
            j = gc.Judge(gc.load(d), self.SCHEMA, gc.load_kit_registry(), gc.load_scale_order(),
                         gc.load_kit_producers(), genome_dir=d)
            j.run(today)
            return j
        finally:
            shutil.rmtree(d)

    def test_o_juiz_acusa_a_prova_datada_do_futuro(self):
        j = self.julgar(("PRF-0069", "date", AMANHA), today=HOJE)
        self.assertTrue(any("depois de hoje" in e for e in j.errors),
                        f"o juiz nao chamou a regra de data; veio {j.errors}")

    def test_a_lei_recusa_a_forma_errada_antes_do_juiz(self):
        """A forma mora no SCHEMA, com `pattern`. Exigir aqui a frase do
        jsonschema e o que faz cair a mutacao que apaga esse `pattern` da lei:
        sem isso o juiz pegaria a mesma data e o caso continuaria verde."""
        j = self.julgar(("PRF-0069", "date", "2026-9-30"), today=HOJE)
        self.assertTrue(any("does not match" in e for e in j.errors), j.errors)

    def test_o_hoje_do_juiz_vem_de_hoje_utc(self):
        """Se alguem trocar `hoje_utc()` de volta por `datetime.date.today()`,
        este caso cai — e so ele, porque os outros passam um `today` explicito."""
        original = gdc.hoje_utc
        gdc.hoje_utc = lambda: "1999-12-31"
        try:
            j = self.julgar()                  # sem today: o juiz escolhe sozinho
            self.assertEqual(j.today, "1999-12-31",
                             "o juiz nao passou por hoje_utc() — voltou ao fuso local?")
            # e o hoje nao e enfeite: e o que a comparacao usa. Com 1999 como
            # hoje, o grafo inteiro de 2026 esta no futuro.
            self.assertTrue(any("depois de hoje" in e for e in j.errors), j.errors)
        finally:
            gdc.hoje_utc = original

    def test_o_grafo_real_tem_todas_as_datas_validas(self):
        j = self.julgar()
        self.assertEqual(gdc.achados(j.kind, j.today), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
