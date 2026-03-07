# Conclusão Automática de Caronas

## Descrição
O sistema pode concluir automaticamente as caronas 24 horas após o horário agendado.

## Como usar

### Execução manual
Para testar ou executar manualmente:
```bash
python manage.py concluir_caronas_auto
```

### Agendamento automático com Cron (Linux/Mac)
Adicione ao seu crontab (`crontab -e`):
```bash
# Executar a cada 1 hora
0 * * * * cd /caminho/para/caronasjp && python manage.py concluir_caronas_auto

# Executar a cada 30 minutos
*/30 * * * * cd /caminho/para/caronasjp && python manage.py concluir_caronas_auto

# Executar a cada 5 minutos
*/5 * * * * cd /caminho/para/caronasjp && python manage.py concluir_caronas_auto
```

### Agendamento automático com Celery (recomendado para produção)
Se você instalar Celery no futuro, pode usar tasks periódicas para maior confiabilidade.

### Agendamento automático no Windows (Task Scheduler)
1. Abra o "Agendador de Tarefas"
2. Clique em "Criar Tarefa"
3. Na aba "Geral":
   - Nome: "Concluir Caronas Automaticamente"
   - Marque "Executar com privilégios mais altos"
4. Na aba "Gatilhos":
   - Novo gatilho
   - Inicie a tarefa: "Em uma agenda"
   - Frequência: "Hora" (a cada 1 hora, por exemplo)
5. Na aba "Ações":
   - Ação: "Iniciar um programa"
   - Programa: `C:\Users\JCServer\caronasjp\venv\Scripts\python.exe`
   - Argumentos: `manage.py concluir_caronas_auto`
   - Começar em: `C:\Users\JCServer\caronasjp`

## O que acontece
- Sistem a verifica todas as caronas com status "ativa"
- Se passou 24 horas desde o horário agendado, marca como "concluída"
- Cria uma notificação para o motorista informando que a viagem foi concluída automaticamente

## Timezone
O sistema usa o timezone configurado no Django (`America/Sao_Paulo`), portanto respeita o horário de Brasília.
