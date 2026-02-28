import os
from num2words import num2words
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_JUSTIFY

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("TOKEN")

(
    PESSOAS,
    DATA_ENTRADA,
    DATA_SAIDA,
    DIAS,
    DIARIA,
    TAXA,
    NOME,
    DOC_TIPO,
    DOC_NUM,
    OBS,
    OBS_TEXTO,
    RESUMO,
) = range(12)


# ------------------ FUNÇÕES AUXILIARES ------------------

def moeda(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


async def mostrar_resumo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dados = context.user_data
    valor_total = dados["diaria"] * dados["dias"]
    entrada = valor_total * 0.3

    resumo = f"""
📋 RESUMO PARA CONFERÊNCIA

Pessoas: {dados['pessoas']}
Entrada: {dados['entrada']}
Saída: {dados['saida']}
Dias: {dados['dias']}
Diária: R$ {moeda(dados['diaria'])}
Taxa: R$ {moeda(dados['taxa'])}
Valor Total: R$ {moeda(valor_total)}
Entrada (30%): R$ {moeda(entrada)}
Nome: {dados['nome']}
Documento: {dados['doc_tipo']} {dados['doc_num']}
Observações: {len(dados.get('obs', []))}
"""

    keyboard = [
        [InlineKeyboardButton("✏️ Editar Pessoas", callback_data="edit_pessoas")],
        [InlineKeyboardButton("✏️ Editar Datas", callback_data="edit_datas")],
        [InlineKeyboardButton("✏️ Editar Valores", callback_data="edit_valores")],
        [InlineKeyboardButton("✏️ Editar Nome", callback_data="edit_nome")],
        [InlineKeyboardButton("✏️ Editar Documento", callback_data="edit_doc")],
        [InlineKeyboardButton("✏️ Editar Observações", callback_data="edit_obs")],
        [InlineKeyboardButton("✅ Confirmar e Gerar PDF", callback_data="confirmar")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(resumo, reply_markup=reply_markup)
    else:
        await update.message.reply_text(resumo, reply_markup=reply_markup)

    return RESUMO


def esta_editando(context):
    return context.user_data.get("editando")


def finalizar_edicao(context):
    context.user_data.pop("editando", None)


# ------------------ FLUXO PRINCIPAL ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Quantas pessoas?")
    return PESSOAS


async def pessoas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pessoas"] = update.message.text

    if esta_editando(context):
        finalizar_edicao(context)
        return await mostrar_resumo(update, context)

    await update.message.reply_text("Data de entrada (DD/MM/AAAA)?")
    return DATA_ENTRADA


async def data_entrada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["entrada"] = update.message.text

    if esta_editando(context):
        finalizar_edicao(context)
        return await mostrar_resumo(update, context)

    await update.message.reply_text("Data de saída (DD/MM/AAAA)?")
    return DATA_SAIDA


async def data_saida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["saida"] = update.message.text

    if esta_editando(context):
        finalizar_edicao(context)
        return await mostrar_resumo(update, context)

    await update.message.reply_text("Quantos dias de estadia?")
    return DIAS


async def dias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["dias"] = int(update.message.text)

    if esta_editando(context):
        finalizar_edicao(context)
        return await mostrar_resumo(update, context)

    await update.message.reply_text("Valor da diária?")
    return DIARIA


async def diaria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["diaria"] = float(update.message.text.replace(",", "."))

    if esta_editando(context):
        finalizar_edicao(context)
        return await mostrar_resumo(update, context)

    await update.message.reply_text("Valor da taxa de limpeza? (0 se não houver)")
    return TAXA


async def taxa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["taxa"] = float(update.message.text.replace(",", "."))

    if esta_editando(context):
        finalizar_edicao(context)
        return await mostrar_resumo(update, context)

    await update.message.reply_text("Nome do locatário?")
    return NOME


async def nome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nome"] = update.message.text

    if esta_editando(context):
        finalizar_edicao(context)
        return await mostrar_resumo(update, context)

    await update.message.reply_text("CPF ou RG?")
    return DOC_TIPO


async def doc_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["doc_tipo"] = update.message.text.upper()

    if esta_editando(context):
        finalizar_edicao(context)
        return await mostrar_resumo(update, context)

    await update.message.reply_text("Número do documento?")
    return DOC_NUM


async def doc_num(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["doc_num"] = update.message.text

    if esta_editando(context):
        finalizar_edicao(context)
        return await mostrar_resumo(update, context)

    await update.message.reply_text("Deseja adicionar observação? (Sim/Não)")
    return OBS


# ------------------ OBS ------------------

async def obs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "sim":
        await update.message.reply_text("Digite a observação:")
        return OBS_TEXTO
    else:
        return await mostrar_resumo(update, context)


async def obs_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "obs" not in context.user_data:
        context.user_data["obs"] = []

    context.user_data["obs"].append(update.message.text)
    await update.message.reply_text("Deseja adicionar outra observação? (Sim/Não)")
    return OBS


# ------------------ BOTÕES ------------------

async def botoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    escolha = query.data

    if escolha == "confirmar":
        return await gerar_pdf(update, context)

    mapa = {
        "edit_pessoas": (PESSOAS, "Quantas pessoas?"),
        "edit_datas": (DATA_ENTRADA, "Data de entrada?"),
        "edit_valores": (DIARIA, "Valor da diária?"),
        "edit_nome": (NOME, "Nome do locatário?"),
        "edit_doc": (DOC_TIPO, "CPF ou RG?"),
        "edit_obs": (OBS, "Deseja adicionar observação? (Sim/Não)"),
    }

    estado, pergunta = mapa[escolha]
    context.user_data["editando"] = True

    if escolha == "edit_obs":
        context.user_data["obs"] = []

    await query.message.reply_text(pergunta)
    return estado


# ------------------ PDF ------------------

async def gerar_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):

    dados = context.user_data
    valor_total = dados["diaria"] * dados["dias"]
    entrada = valor_total * 0.3

    nome_arquivo = f"CONTRATO DE LOCAÇÃO - {dados['nome']}.pdf"

    doc = SimpleDocTemplate(nome_arquivo, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    estilo = ParagraphStyle(
        "Justificado",
        parent=styles["Normal"],
        alignment=TA_JUSTIFY,
        fontSize=11,
        leading=15,
    )

    texto = f"""
<b>CONTRATO DE LOCAÇÃO – APTO NO EDIFÍCIO ILHA DO MEL – 
Rua Guaraci, 1568 apto 401 – Capão da Canoa – RS</b><br/><br/>

Referente ao aluguel do apartamento para {dados['pessoas']} pessoas 
(incluindo crianças), contendo 2 quartos, sala, cozinha e 1 banheiro, 
ventiladores de teto instalados nos quartos e na sala, TV, churrasqueira 
individual e utensílios de cozinha, máquina de lavar, cozinha com geladeira, 
liquidificador, cafeteira, torradeira, fogão com botijão de gás, 
3 cadeiras de praia com carrinho.<br/><br/>

Para que todos tenham uma excelente estadia durante o período que estejam 
como hóspedes em nosso apartamento, solicitamos observar os itens abaixo:<br/><br/>

Não é permitido número de pessoas maior do que será estipulado neste contrato 
e nem visitas que utilizem a estrutura do apartamento. Caso isto ocorra será 
cobrada uma multa de R$200,00 por dia por pessoa.<br/><br/>

Informar se houver alguma irregularidade no imóvel, bem como falta de objetos 
ao entrar no apartamento. Favor não sentar ou deitar nos sofás e camas com o 
corpo molhado. Atenção a tensão (voltagem) das tomadas do apartamento, as 
tomadas são todas 110 volts. Não é permitido fumar no interior do apartamento, 
bem como uso de aparelhos de áudio em volume alto que possa perturbar os demais 
usuários e vizinhos do condomínio. Solicitamos o uso consciente e sustentável 
da energia e água, manter as janelas fechadas quando tiver chovendo e ventiladores 
desligados quando estiver ausente do imóvel. Atenção ao horário de silêncio das 
22h às 7h. Não nos responsabilizamos por acidentes de qualquer natureza, bem 
como furtos de pertences dentro do apartamento e nos carros, sendo de 
responsabilidade do locatário.<br/><br/>

O período de estadia do locatário será de {dados['dias']} dias, iniciando às 14h 
do dia {dados['entrada']} e término dia {dados['saida']} às 12h, valor a ser pago 
de R$ {moeda(valor_total)} ({num2words(valor_total, lang="pt_BR")} reais) mais 
R$ {moeda(dados['taxa'])} ({num2words(dados['taxa'], lang="pt_BR")} reais) 
pela taxa de limpeza, referente a locação do apartamento, sendo na reserva 
R$ {moeda(entrada)} ({num2words(entrada, lang="pt_BR")} reais), correspondente 
a 30% do valor total. Este valor deverá ser depositado via Pix: 88816966068, 
em nome de Zeva Suzana Noronha Henz. O saldo restante deverá ser pago na 
entrega da chave. Em caso de desistência por parte do locatário, o mesmo deverá 
comunicar o locador 30 dias antes do início do período de locação para que 
possa ser feita a devolução da reserva. Caso não haja comunicação no prazo 
de 30 dias, o locador não se sentirá na obrigação de devolver o valor da 
reserva acima mencionado.<br/><br/>
"""

    for o in dados.get("obs", []):
        texto += f"Obs; {o}<br/><br/>"

    texto += f"""
( X ) Aceito os termos do contrato.<br/><br/><br/>

___________________________________<br/>
{dados['nome']} (Locatário)<br/>
{dados['doc_tipo']}: {dados['doc_num']}<br/><br/>

___________________________________<br/>
Zeva Suzana Noronha Henz (Locadora)<br/>
CPF: 888.169.660-68
"""

    elements.append(Paragraph(texto, estilo))
    doc.build(elements)

    await update.callback_query.message.reply_document(document=open(nome_arquivo, "rb"))
    os.remove(nome_arquivo)

    return ConversationHandler.END


# ------------------ MAIN ------------------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PESSOAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, pessoas)],
            DATA_ENTRADA: [MessageHandler(filters.TEXT & ~filters.COMMAND, data_entrada)],
            DATA_SAIDA: [MessageHandler(filters.TEXT & ~filters.COMMAND, data_saida)],
            DIAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, dias)],
            DIARIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, diaria)],
            TAXA: [MessageHandler(filters.TEXT & ~filters.COMMAND, taxa)],
            NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, nome)],
            DOC_TIPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, doc_tipo)],
            DOC_NUM: [MessageHandler(filters.TEXT & ~filters.COMMAND, doc_num)],
            OBS: [MessageHandler(filters.TEXT & ~filters.COMMAND, obs)],
            OBS_TEXTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, obs_texto)],
            RESUMO: [CallbackQueryHandler(botoes)],
        },
        fallbacks=[],
    )

    app.add_handler(conv)
    app.run_polling()


if __name__ == "__main__":
    main()