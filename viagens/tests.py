from datetime import timedelta, time
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import get_template
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import CaronaForm, SolicitacaoForm
from .models import Carona, Solicitacao, Veiculo, Notificacao


@override_settings(
    STORAGES={"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}},
    VAPID_PUBLIC_KEY="", VAPID_PRIVATE_KEY="",
)
class ChecklistTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model().objects
        cls.motorista = users.create_user(email="motorista@example.test", password="test", nome_completo="Motorista", telefone="11911111111")
        cls.passageiro = users.create_user(email="passageiro@example.test", password="test", nome_completo="Passageiro", telefone="11922222222")
        cls.outro = users.create_user(email="outro@example.test", password="test")
        cls.veiculo = Veiculo.objects.create(motorista=cls.motorista, tipo="carro", marca="Teste", modelo="Teste", cor="Azul", ano=2024)
        cls.carona = Carona.objects.create(motorista=cls.motorista, veiculo=cls.veiculo, origem="Origem", destino="Destino", data=timezone.localdate()+timedelta(days=2), hora=time(12), vagas=4, tipo_valor="dinheiro", valor=20)

    def reserva(self, **kwargs):
        dados = dict(carona=self.carona, solicitante=self.passageiro, nome_solicitante="Contato", telefone_solicitante="11933333333", quantidade=2, tipo="carona", status="aceita")
        dados.update(kwargs)
        return Solicitacao.objects.create(**dados)

    def editar(self, reserva, quantidade, **kwargs):
        return self.client.post(reverse("editar_vagas", args=[reserva.pk]), {"quantidade": quantidade, **kwargs})

    def test_aumento_exige_nova_aprovacao_e_notifica_motorista(self):
        reserva = self.reserva()
        self.client.force_login(self.passageiro)
        resposta = self.editar(reserva, 3)
        self.assertEqual(resposta.status_code, 200)
        reserva.refresh_from_db()
        self.assertEqual((reserva.quantidade, reserva.status), (3, "pendente"))
        self.assertTrue(Notificacao.objects.filter(usuario=self.motorista, solicitacao=reserva).exists())

    def test_reducao_mantem_confirmacao(self):
        reserva = self.reserva()
        self.client.force_login(self.passageiro)
        self.assertEqual(self.editar(reserva, 1).status_code, 200)
        reserva.refresh_from_db()
        self.assertEqual((reserva.quantidade, reserva.status), (1, "aceita"))

    def test_limite_considera_outros_passageiros(self):
        reserva = self.reserva()
        self.reserva(solicitante=self.outro, quantidade=2)
        self.client.force_login(self.passageiro)
        self.assertEqual(self.editar(reserva, 3).status_code, 400)
        reserva.refresh_from_db()
        self.assertEqual(reserva.quantidade, 2)

    def test_quantidades_invalidas_nao_alteram_reserva(self):
        reserva = self.reserva()
        self.client.force_login(self.passageiro)
        for quantidade in [0, -1, "1.5", "abc", 999]:
            with self.subTest(quantidade=quantidade):
                self.assertEqual(self.editar(reserva, quantidade).status_code, 400)
        reserva.refresh_from_db()
        self.assertEqual(reserva.quantidade, 2)

    def test_reserva_logada_so_pode_ser_editada_pelo_titular(self):
        reserva = self.reserva()
        for user in [self.outro, self.motorista]:
            self.client.force_login(user)
            self.assertEqual(self.editar(reserva, 1, token=str(reserva.token_cancelamento)).status_code, 403)
        self.client.logout()
        self.assertEqual(self.editar(reserva, 1, token=str(reserva.token_cancelamento)).status_code, 403)

    def test_visitante_precisa_token_correto(self):
        reserva = self.reserva(solicitante=None)
        self.assertEqual(self.editar(reserva, 1).status_code, 403)
        self.assertEqual(self.editar(reserva, 1, token="invalido").status_code, 403)
        self.assertEqual(self.editar(reserva, 1, token=str(reserva.token_cancelamento)).status_code, 200)

    def test_edicao_exige_post_e_csrf(self):
        from django.test import Client
        reserva = self.reserva(solicitante=None)
        url = reverse("editar_vagas", args=[reserva.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(Client(enforce_csrf_checks=True).post(url, {"quantidade": 1, "token": str(reserva.token_cancelamento)}).status_code, 403)

    def test_nao_edita_reserva_cancelada_ou_viagem_encerrada(self):
        reserva = self.reserva(status="cancelada")
        self.client.force_login(self.passageiro)
        self.assertEqual(self.editar(reserva, 1).status_code, 400)
        reserva.status = "aceita"
        reserva.save()
        self.carona.status = "concluida"
        self.carona.save()
        self.assertEqual(self.editar(reserva, 1).status_code, 400)

    def test_modalidades_bloqueiam_acesso_direto(self):
        self.carona.modalidade = "encomenda"
        self.carona.save()
        self.assertEqual(self.client.get(reverse("solicitar_vaga", args=[self.carona.pk])).status_code, 400)
        self.carona.modalidade = "carona"
        self.carona.save()
        self.assertEqual(self.client.get(reverse("solicitar_encomenda", args=[self.carona.pk])).status_code, 400)

    def test_motorista_pode_bloquear_e_reabrir_encomendas(self):
        url_status = reverse("definir_status_encomendas", args=[self.carona.pk])
        url_encomenda = reverse("solicitar_encomenda", args=[self.carona.pk])
        self.client.force_login(self.motorista)

        self.assertEqual(self.client.get(url_status).status_code, 405)
        self.assertEqual(self.client.post(url_status, {"estado": "bloquear"}).status_code, 302)
        self.carona.refresh_from_db()
        self.assertFalse(self.carona.encomendas_abertas)

        self.client.logout()
        self.assertEqual(self.client.get(url_encomenda).status_code, 400)

        self.client.force_login(self.motorista)
        self.assertEqual(self.client.post(url_status, {"estado": "abrir"}).status_code, 302)
        self.carona.refresh_from_db()
        self.assertTrue(self.carona.encomendas_abertas)

    def test_observacoes_do_motorista_exigem_confirmacao_nas_duas_solicitacoes(self):
        self.carona.observacoes = "Chegar dez minutos antes e levar documento."
        self.carona.save(update_fields=["observacoes"])
        self.client.force_login(self.passageiro)

        dados_contato = {
            "nome_solicitante": "Passageiro",
            "telefone_solicitante": "11922222222",
            "endereco_solicitante": "Rua A, 10",
            "endereco_destino_solicitante": "Rua B, 20",
        }
        url_vaga = reverse("solicitar_vaga", args=[self.carona.pk])
        response = self.client.post(url_vaga, {**dados_contato, "quantidade": 1, "malas": 0})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Este campo é obrigatório")
        self.assertFalse(Solicitacao.objects.filter(carona=self.carona, tipo="carona").exists())

        response = self.client.post(url_vaga, {
            **dados_contato,
            "quantidade": 1,
            "malas": 0,
            "ciente_observacoes": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Solicitacao.objects.filter(carona=self.carona, tipo="carona").exists())

        url_encomenda = reverse("solicitar_encomenda", args=[self.carona.pk])
        response = self.client.post(url_encomenda, {**dados_contato, "descricao_item": "Uma caixa"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chegar dez minutos antes")
        self.assertFalse(Solicitacao.objects.filter(carona=self.carona, tipo="encomenda").exists())

        response = self.client.post(url_encomenda, {
            **dados_contato,
            "descricao_item": "Uma caixa",
            "ciente_observacoes": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Solicitacao.objects.filter(carona=self.carona, tipo="encomenda").exists())

    def test_outro_usuario_nao_altera_status_das_encomendas(self):
        self.client.force_login(self.outro)
        response = self.client.post(
            reverse("definir_status_encomendas", args=[self.carona.pk]),
            {"estado": "bloquear"},
        )
        self.assertEqual(response.status_code, 404)
        self.carona.refresh_from_db()
        self.assertTrue(self.carona.encomendas_abertas)

    def form_carona(self, **kwargs):
        dados = dict(origem="Origem", destino="Destino", data=self.carona.data.isoformat(), hora="12:00", modalidade="ambos", vagas=4, tipo_valor="dinheiro", valor=20, veiculo=self.veiculo.pk)
        dados.update(kwargs)
        return dados

    def test_somente_encomendas_nao_exige_vagas_nem_passagem(self):
        form = CaronaForm(self.form_carona(modalidade="encomenda", vagas="", tipo_valor="", valor=""), user=self.motorista)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["vagas"], 0)
        self.assertEqual(form.cleaned_data["tipo_valor"], "combinar")

    def test_mudar_modalidade_nao_invalida_solicitacoes(self):
        self.reserva()
        form = CaronaForm(self.form_carona(modalidade="encomenda"), instance=self.carona, user=self.motorista)
        self.assertFalse(form.is_valid())
        self.assertIn("modalidade", form.errors)

    def test_nao_reduz_capacidade_abaixo_de_confirmadas(self):
        self.reserva()
        form = CaronaForm(self.form_carona(vagas=1), instance=self.carona, user=self.motorista)
        self.assertFalse(form.is_valid())
        self.assertIn("vagas", form.errors)

    def test_nova_solicitacao_respeita_limite_no_servidor(self):
        form = SolicitacaoForm({"quantidade": 5}, vagas_disponiveis=4)
        self.assertFalse(form.is_valid())
        self.assertIn("quantidade", form.errors)
        self.assertEqual(form.fields["quantidade"].widget.attrs["max"], 4)

    def test_cancelar_preserva_viagem_e_cancela_pendentes(self):
        reserva = self.reserva(status="pendente")
        self.client.force_login(self.motorista)
        self.assertEqual(self.client.post(reverse("excluir_carona", args=[self.carona.pk])).status_code, 302)
        self.carona.refresh_from_db()
        reserva.refresh_from_db()
        self.assertEqual(self.carona.status, "cancelada")
        self.assertEqual(reserva.status, "cancelada")

    def test_telas_e_telefone_do_formulario(self):
        self.reserva(status="pendente")
        self.client.force_login(self.motorista)
        response = self.client.get(reverse("gerenciar_solicitacoes"))
        self.assertContains(response, "11933333333")
        self.assertNotContains(response, "11922222222")
        for name in ["lista_caronas", "criar_carona", "minhas_caronas"]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        self.assertEqual(self.client.get(reverse("editar_carona", args=[self.carona.pk])).status_code, 200)

    def test_passageiro_ve_editar_e_cancelar_no_modal(self):
        self.reserva()
        self.client.force_login(self.passageiro)
        for name in ["lista_caronas", "minhas_viagens"]:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertContains(response, 'data-id="')
                self.assertContains(response, "Cancelar participação")

    def test_todos_templates_compilam(self):
        for root in [Path(settings.BASE_DIR)/"templates", Path(settings.BASE_DIR)/"viagens/templates"]:
            for path in root.rglob("*.html"):
                with self.subTest(path=path):
                    get_template(path.relative_to(root).as_posix())

    def test_visitantes_e_modalidades_renderizam(self):
        for modalidade in ["ambos", "carona", "encomenda"]:
            self.carona.modalidade = modalidade
            self.carona.save()
            response = self.client.get(reverse("lista_caronas"))
            self.assertEqual(response.status_code, 200)
            if modalidade == "encomenda":
                self.assertNotContains(response, reverse("solicitar_vaga", args=[self.carona.pk]))
            if modalidade == "carona":
                self.assertNotContains(response, reverse("solicitar_encomenda", args=[self.carona.pk]))
        for name in ["minhas_viagens", "minhas_solicitacoes", "minhas_encomendas_passageiro"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_filtros_de_servico_respeitam_modalidade_e_bloqueio(self):
        somente_carona = Carona.objects.create(
            motorista=self.motorista, veiculo=self.veiculo, origem="A", destino="B",
            data=self.carona.data, hora=time(13), vagas=2, modalidade="carona",
            tipo_valor="gratuita",
        )
        somente_encomenda = Carona.objects.create(
            motorista=self.motorista, veiculo=self.veiculo, origem="C", destino="D",
            data=self.carona.data, hora=time(14), vagas=0, modalidade="encomenda",
            tipo_valor="combinar",
        )

        response = self.client.get(reverse("lista_caronas"), {"servicos": "carona"})
        ids = {carona.pk for carona in response.context["caronas"]}
        self.assertIn(self.carona.pk, ids)
        self.assertIn(somente_carona.pk, ids)
        self.assertNotIn(somente_encomenda.pk, ids)

        somente_encomenda.encomendas_abertas = False
        somente_encomenda.save(update_fields=["encomendas_abertas"])
        response = self.client.get(reverse("lista_caronas"), {"servicos": "encomenda"})
        ids = {carona.pk for carona in response.context["caronas"]}
        self.assertIn(self.carona.pk, ids)
        self.assertNotIn(somente_carona.pk, ids)
        self.assertNotIn(somente_encomenda.pk, ids)

    def test_card_exibe_tags_e_badge_voce(self):
        self.client.force_login(self.motorista)
        response = self.client.get(reverse("lista_caronas"))
        self.assertContains(response, ">Carona</span>")
        self.assertContains(response, "Envio de encomendas")
        self.assertNotContains(response, "Carona disponível")
        self.assertContains(response, '<span class="badge bg-primary text-white">Você</span>', html=True)

    def test_dinheiro_e_padrao_em_nova_viagem(self):
        self.assertEqual(CaronaForm(user=self.motorista)["tipo_valor"].value(), "dinheiro")

    def test_motorista_nao_aceita_mais_que_capacidade(self):
        self.reserva(quantidade=3)
        pendente = self.reserva(solicitante=self.outro, quantidade=2, status="pendente")
        self.client.force_login(self.motorista)
        self.client.get(reverse("aceitar_solicitacao", args=[pendente.pk]))
        pendente.refresh_from_db()
        self.assertEqual(pendente.status, "pendente")

    def test_concluir_carona_cancela_pendentes_e_preserva_aceitas(self):
        aceita = self.reserva(status="aceita")
        pendente = self.reserva(solicitante=self.outro, status="pendente")
        self.client.force_login(self.motorista)

        response = self.client.get(reverse("concluir_carona", args=[self.carona.pk]))

        self.assertEqual(response.status_code, 302)
        self.carona.refresh_from_db()
        aceita.refresh_from_db()
        pendente.refresh_from_db()
        self.assertEqual(self.carona.status, "concluida")
        self.assertEqual(aceita.status, "aceita")
        self.assertEqual(pendente.status, "cancelada")

    def test_modal_do_motorista_exibe_apenas_abas_da_modalidade(self):
        self.client.force_login(self.motorista)

        self.carona.modalidade = "carona"
        self.carona.save(update_fields=["modalidade"])
        response = self.client.get(reverse("lista_caronas"))
        self.assertContains(response, f'id="painelPassageiros{self.carona.pk}"')
        self.assertNotContains(response, f'id="painelEncomendas{self.carona.pk}"')

        self.carona.modalidade = "encomenda"
        self.carona.save(update_fields=["modalidade"])
        response = self.client.get(reverse("lista_caronas"))
        self.assertNotContains(response, f'id="painelPassageiros{self.carona.pk}"')
        self.assertContains(response, f'id="painelEncomendas{self.carona.pk}"')

    def test_historico_mostra_participantes_e_remetentes(self):
        self.carona.status = "concluida"
        self.carona.save(update_fields=["status"])
        self.reserva(status="aceita")
        Solicitacao.objects.create(
            carona=self.carona,
            solicitante=self.passageiro,
            nome_solicitante="Passageiro",
            telefone_solicitante="11922222222",
            tipo="encomenda",
            status="aceita",
            descricao_item="Caixa de livros",
        )
        self.client.force_login(self.motorista)

        response = self.client.get(reverse("historico_viagens"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Passageiro")
        self.assertContains(response, "Caixa de livros")
        self.assertContains(response, "Remetente")
        self.assertContains(response, "Origem -> Destino", count=1)

    def test_rotulo_de_status_concluida_esta_correto(self):
        self.carona.status = "concluida"
        self.assertEqual(self.carona.get_status_display(), "Concluída")
