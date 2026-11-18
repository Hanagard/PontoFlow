# Publicação de demonstração — PontoFlow

Este repositório está preparado para uma implantação de demonstração em Render + MongoDB Atlas. O deploy não é automático: exige que o proprietário conecte o repositório e configure a URI do banco. Nenhuma credencial deve ser colocada no Git.

## Arquitetura
- Render Web Service (Docker): FastAPI + frontend React compilado, mesma origem HTTPS.
- MongoDB Atlas: banco persistente separado da aplicação.
- GitHub Actions: testes e build; não hospeda a aplicação.

## 1. Criar banco MongoDB Atlas
1. Crie uma conta em https://www.mongodb.com/atlas/database.
2. Crie um cluster Free (M0) e um usuário de banco com senha forte.
3. Em Network Access, permita a conexão do Render. Para uma demonstração inicial, pode-se usar 0.0.0.0/0 somente com usuário/senha fortes e banco de demonstração; prefira restringir por IP quando possível.
4. Copie a connection string mongodb+srv://..., substituindo usuário, senha e nome do banco.
5. Não coloque a URI em arquivos, commits ou mensagens públicas.

## 2. Criar serviço no Render
1. Acesse https://dashboard.render.com/ e conecte o GitHub.
2. Escolha New > Blueprint e selecione Hanagard/PontoFlow.
3. Selecione a branch audit/hardening-2026-11 para a demonstração.
4. O Render reconhecerá render.yaml e criará o serviço Docker pontoflow-demo.
5. Na configuração Environment do serviço, defina MONGO_URL com a URI privada do Atlas. SESSION_SECRET será gerado pelo Render.
6. Faça o deploy manual após revisar as variáveis. O serviço usa APP_ENV=production, HTTPS e cookie Secure.

O plano Free pode suspender o serviço após inatividade e a primeira abertura pode demorar. Não é adequado para produção comercial com SLA.

## 3. Popular dados de demonstração (opcional)
O seed é destrutivo apenas para a empresa de demonstração e usa credenciais fixas de teste. Execute-o somente em um banco Atlas criado exclusivamente para a demonstração, nunca no banco de clientes.

Com Python 3.12 e dependências instaladas, no seu computador:

    cd backend
    pip install -r requirements.txt
    # Configure MONGO_URL e DB_NAME no ambiente local, apontando para o banco demo isolado.
    python seed.py

O seed informa a senha de demonstração ao terminar. Os usuários são admin@pontoflow.com.br (administrador), super@pontoflow.com.br (super administrador), gestor@pontoflow.com.br (gestor) e maria.silva@pontoflow.com.br (funcionário).

Senha inicial do seed: Ponto@2026. Altere/remova as contas e a senha antes de qualquer exposição pública. Não disponibilize a demonstração com essa senha conhecida.

## 4. Verificação
- Abra https://SEU-SERVICO.onrender.com/api/; deve retornar a mensagem PontoFlow API.
- Abra a raiz do serviço; deve carregar o React.
- Teste login, logout, sessão, jornada, solicitações e painel.
- Confirme cookie Secure, HttpOnly e SameSite=Lax.
- Não use dados pessoais reais na demonstração.

## Limitações e produção
Esta configuração não transforma o produto em sistema homologado legalmente para registro de ponto. Antes de vender como solução de produção, concluir revisão jurídica/regulatória, LGPD, backup e restauração, monitoramento, rate limit distribuído, e-mail/recuperação de conta, teste de carga, revisão de segurança e contrato/SLA.

O deploy depende de ações manuais no Render e Atlas e de aceitar seus termos. O GitHub Actions não cria contas nesses serviços nem pode configurar segredos externos em seu nome.