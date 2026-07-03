# -*- coding: utf-8 -*-
"""
FC26 Nitelik Takip Botu
========================
Özellikler:
  .s [@kullanıcı]        -> Nitelikleri gösterir (kalıcı + bu haftaki)
  .nitver @kullanıcı <nitelik> <miktar>  -> Nitelik ekler (sadece yetkili rol)
  .nital @kullanıcı <nitelik> <miktar>   -> Nitelik azaltır (sadece yetkili rol)
  .fixyap                -> Bu haftaki nitelikleri kalıcıya aktarır, haftalığı sıfırlar (sadece Taç rolü)
  .haftaliktop            -> Bu hafta en çok nitelik kasanları sıralar (kim ne kastı dahil)
  .aiac                   -> AI'yi açar (sadece sunucu sahibi)
  .aikapat                -> AI'yi kapatır (sadece sunucu sahibi)
  .ai <mesaj>              -> AI ile konuşur (açıksa herkes kullanabilir)

Kurulum:
  1) pip install -r requirements.txt
  2) Aşağıdaki CONFIG bölümünü doldur (BOT_TOKEN, TAC_ROLE_ID, ANTHROPIC_API_KEY vb.)
  3) python bot.py
"""

import json
import os
from datetime import datetime, timezone

import discord
from discord.ext import commands

# =========================================================
#                        CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "BURAYA_BOT_TOKENINI_YAZ")

# .nitver / .nital komutlarını kullanabilecek "nitelik yetkilisi" rolü
YETKILI_ROLE_ID = 1522570877626220615

# .fixyap komutunu kullanabilecek "Taç" rolünün ID'si.
# Sunucundaki Taç rolüne sağ tıklayıp "ID'yi Kopyala" diyerek buraya yapıştır.
TAC_ROLE_ID = 0  # <-- BURAYI DOLDUR

# AI için Anthropic API key (https://console.anthropic.com)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

DATA_FILE = "data.json"
PREFIX = "."

# =========================================================
#                     VERİ YÖNETİMİ
# =========================================================

def veri_yukle():
    if not os.path.exists(DATA_FILE):
        return {"kullanicilar": {}, "ai_acik": False}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"kullanicilar": {}, "ai_acik": False}


def veri_kaydet(veri):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)


VERI = veri_yukle()


def kullanici_al(user_id: int):
    uid = str(user_id)
    if uid not in VERI["kullanicilar"]:
        VERI["kullanicilar"][uid] = {"haftalik": {}, "kalici": {}}
        veri_kaydet(VERI)
    return VERI["kullanicilar"][uid]


# =========================================================
#                        BOT KURULUMU
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)


# =========================================================
#                      YETKİ KONTROLLERİ
# =========================================================

def sunucu_sahibi_mi():
    async def predicate(ctx: commands.Context):
        if ctx.guild is None:
            return False
        if ctx.author.id != ctx.guild.owner_id:
            await ctx.reply("❌ Bu komutu sadece sunucu sahibi kullanabilir.")
            return False
        return True
    return commands.check(predicate)


def tac_rolu_mu():
    async def predicate(ctx: commands.Context):
        if ctx.guild is None:
            return False
        rol = ctx.guild.get_role(TAC_ROLE_ID)
        if rol is None or rol not in ctx.author.roles:
            await ctx.reply("❌ Bu komutu sadece **Taç** rolüne sahip kişi kullanabilir.")
            return False
        return True
    return commands.check(predicate)


def yetkili_rolu_mu():
    async def predicate(ctx: commands.Context):
        if ctx.guild is None:
            return False
        rol = ctx.guild.get_role(YETKILI_ROLE_ID)
        if rol is None or rol not in ctx.author.roles:
            await ctx.reply(f"❌ Bu komutu sadece <@&{YETKILI_ROLE_ID}> rolüne sahip kişiler kullanabilir.")
            return False
        return True
    return commands.check(predicate)


# =========================================================
#                          EVENTS
# =========================================================

@bot.event
async def on_ready():
    print(f"[OK] Giriş yapıldı: {bot.user} ({bot.user.id})")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        return  # Uyarı zaten check içinde gönderildi
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply(f"⚠️ Eksik parametre var. Kullanım: `{PREFIX}{ctx.command} {ctx.command.signature}`")
        return
    if isinstance(error, commands.BadArgument):
        await ctx.reply("⚠️ Kullanıcı veya sayı formatı hatalı. Örn: `.nitver @kullanici Hız 3`")
        return
    if isinstance(error, commands.CommandNotFound):
        return
    raise error


# =========================================================
#                    .s  -> NİTELİKLERİ GÖSTER
# =========================================================

@bot.command(name="s")
async def s(ctx: commands.Context, hedef: discord.Member = None):
    """Kalıcı ve haftalık nitelikleri gösterir."""
    hedef = hedef or ctx.author
    veri = kullanici_al(hedef.id)

    kalici = veri["kalici"]
    haftalik = veri["haftalik"]

    embed = discord.Embed(
        title=f"📊 {hedef.display_name} - Nitelikler",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_thumbnail(url=hedef.display_avatar.url)

    if kalici:
        kalici_metin = "\n".join(f"**{k}:** {v}" for k, v in sorted(kalici.items()))
    else:
        kalici_metin = "Henüz kalıcı nitelik yok."
    embed.add_field(name="🏆 Kalıcı Nitelikler", value=kalici_metin, inline=False)

    if haftalik:
        haftalik_metin = "\n".join(f"**{k}:** {v}" for k, v in sorted(haftalik.items()))
    else:
        haftalik_metin = "Bu hafta henüz nitelik kazanılmadı."
    embed.add_field(name="📅 Bu Haftaki Nitelikler", value=haftalik_metin, inline=False)

    toplam_kalici = sum(kalici.values()) if kalici else 0
    toplam_haftalik = sum(haftalik.values()) if haftalik else 0
    embed.set_footer(text=f"Toplam kalıcı: {toplam_kalici}  |  Bu hafta: {toplam_haftalik}")

    await ctx.reply(embed=embed)


# =========================================================
#                .nitver / .nital -> NİTELİK VER/AL
# =========================================================

@bot.command(name="nitver")
@yetkili_rolu_mu()
async def nitver(ctx: commands.Context, hedef: discord.Member, nitelik: str, miktar: int):
    """Kullanıcının haftalık niteliğine ekleme yapar."""
    if miktar <= 0:
        await ctx.reply("⚠️ Miktar pozitif bir sayı olmalı.")
        return

    veri = kullanici_al(hedef.id)
    veri["haftalik"][nitelik] = veri["haftalik"].get(nitelik, 0) + miktar
    veri_kaydet(VERI)

    await ctx.reply(
        f"✅ {ctx.author.mention}, {hedef.mention} kullanıcısına **{nitelik}** niteliğinden "
        f"**+{miktar}** verdi. (Bu haftaki toplam: {veri['haftalik'][nitelik]})"
    )


@bot.command(name="nital")
@yetkili_rolu_mu()
async def nital(ctx: commands.Context, hedef: discord.Member, nitelik: str, miktar: int):
    """Kullanıcının haftalık niteliğinden düşer (0'ın altına inmez)."""
    if miktar <= 0:
        await ctx.reply("⚠️ Miktar pozitif bir sayı olmalı.")
        return

    veri = kullanici_al(hedef.id)
    mevcut = veri["haftalik"].get(nitelik, 0)
    yeni = max(0, mevcut - miktar)
    veri["haftalik"][nitelik] = yeni
    veri_kaydet(VERI)

    await ctx.reply(
        f"✅ {ctx.author.mention}, {hedef.mention} kullanıcısının **{nitelik}** niteliğinden "
        f"**-{miktar}** aldı. (Bu haftaki toplam: {yeni})"
    )


# =========================================================
#                  .fixyap -> HAFTALIĞI KALICIYA AKTAR
# =========================================================

@bot.command(name="fixyap")
@tac_rolu_mu()
async def fixyap(ctx: commands.Context):
    """Tüm kullanıcıların haftalık niteliklerini kalıcıya ekler ve haftalığı sıfırlar."""
    etkilenen = 0
    for uid, veri in VERI["kullanicilar"].items():
        if not veri["haftalik"]:
            continue
        for nitelik, miktar in veri["haftalik"].items():
            veri["kalici"][nitelik] = veri["kalici"].get(nitelik, 0) + miktar
        veri["haftalik"] = {}
        etkilenen += 1

    veri_kaydet(VERI)

    embed = discord.Embed(
        title="🔒 Haftalık Nitelikler Kalıcıya Aktarıldı",
        description=f"{etkilenen} kullanıcının haftalık nitelikleri kalıcı niteliklerine eklendi "
                     f"ve haftalık sayaç sıfırlandı.",
        color=discord.Color.green(),
    )
    embed.set_footer(text=f"İşlemi yapan: {ctx.author.display_name}")
    await ctx.reply(embed=embed)


# =========================================================
#              .haftaliktop -> HAFTALIK SIRALAMA
# =========================================================

@bot.command(name="haftaliktop")
async def haftaliktop(ctx: commands.Context):
    """Bu hafta en çok nitelik kasan kullanıcıları, neyi ne kadar kastıklarıyla sıralar."""
    siralama = []
    for uid, veri in VERI["kullanicilar"].items():
        haftalik = veri["haftalik"]
        if not haftalik:
            continue
        toplam = sum(haftalik.values())
        siralama.append((uid, toplam, haftalik))

    if not siralama:
        await ctx.reply("📭 Bu hafta henüz kimse nitelik kasmamış.")
        return

    siralama.sort(key=lambda x: x[1], reverse=True)

    embed = discord.Embed(
        title="🏅 Haftalık Nitelik Sıralaması",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc),
    )

    madalyalar = ["🥇", "🥈", "🥉"]
    for i, (uid, toplam, haftalik) in enumerate(siralama[:15]):
        madalya = madalyalar[i] if i < 3 else f"#{i+1}"
        uye = ctx.guild.get_member(int(uid))
        isim = uye.display_name if uye else f"Kullanıcı ({uid})"
        detay = ", ".join(f"{k}: +{v}" for k, v in sorted(haftalik.items(), key=lambda x: -x[1]))
        embed.add_field(
            name=f"{madalya} {isim} — Toplam: {toplam}",
            value=detay,
            inline=False,
        )

    await ctx.reply(embed=embed)


# =========================================================
#                     .aiac / .aikapat
# =========================================================

@bot.command(name="aiac")
@sunucu_sahibi_mi()
async def aiac(ctx: commands.Context):
    VERI["ai_acik"] = True
    veri_kaydet(VERI)
    await ctx.reply("🤖 AI **açıldı**.")


@bot.command(name="aikapat")
@sunucu_sahibi_mi()
async def aikapat(ctx: commands.Context):
    VERI["ai_acik"] = False
    veri_kaydet(VERI)
    await ctx.reply("🤖 AI **kapatıldı**.")


# =========================================================
#                          .ai
# =========================================================

async def claude_yanit_al(mesaj: str) -> str:
    """Anthropic API üzerinden yanıt alır. API key ayarlanmadıysa uyarı döner."""
    if not ANTHROPIC_API_KEY:
        return "⚠️ ANTHROPIC_API_KEY ayarlanmamış, AI şu an cevap veremiyor."

    try:
        import anthropic
    except ImportError:
        return "⚠️ `anthropic` kütüphanesi kurulu değil. `pip install anthropic` çalıştır."

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{"role": "user", "content": mesaj}],
        )
        parcalar = [b.text for b in response.content if b.type == "text"]
        return "\n".join(parcalar) if parcalar else "🤖 (boş yanıt)"
    except Exception as e:
        return f"⚠️ AI isteğinde hata oluştu: {e}"


@bot.command(name="ai")
async def ai(ctx: commands.Context, *, mesaj: str = None):
    if not VERI.get("ai_acik", False):
        await ctx.reply("🤖 AI şu anda kapalı. Sunucu sahibi `.aiac` ile açabilir.")
        return

    if not mesaj:
        await ctx.reply(f"⚠️ Bir mesaj yaz. Örn: `{PREFIX}ai merhaba`")
        return

    async with ctx.typing():
        cevap = await claude_yanit_al(mesaj)

    await ctx.reply(cevap[:2000])  # Discord mesaj sınırı


# =========================================================
#                          ÇALIŞTIR
# =========================================================

if __name__ == "__main__":
    if BOT_TOKEN == "BURAYA_BOT_TOKENINI_YAZ":
        print("[HATA] BOT_TOKEN ayarlanmamış. bot.py içindeki CONFIG bölümünü doldur "
              "ya da BOT_TOKEN ortam değişkenini ayarla.")
    else:
        bot.run(BOT_TOKEN)
