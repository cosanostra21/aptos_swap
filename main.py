import asyncio
import requests
from aptos_sdk.account import Account
from aptos_sdk.async_client import RestClient
from aptos_sdk.transactions import EntryFunction, TransactionPayload, TransactionArgument
from aptos_sdk.bcs import Serializer
from aptos_sdk.type_tag import TypeTag, StructTag


private_key = 'your_key'

NODE_URL = "https://fullnode.mainnet.aptoslabs.com/v1"
account = Account.load_key(private_key)

MODULE = "0x9dd974aea0f927ead664b9e1c295e4215bd441a9fb4e53e5ea0bf22f356c8a2b::router"
FUNCTION = "swap_exact_coin_for_coin_x1"

SLIPPAGE = 0.02  # 2%
STEP_INDEX = [0]

APT = "0x1::aptos_coin::AptosCoin"
USDC = "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC"
CURVE = "0x190d44266241744264b964a37b8f09863167a12d3e70cda39376cfb4e3561e12::curves::Uncorrelated"
BINSTEP = "0x9dd974aea0f927ead664b9e1c295e4215bd441a9fb4e53e5ea0bf22f356c8a2b::router::BinStepV0V05"

def get_apt_price_usd():
    url = "https://api.coingecko.com/api/v3/simple/price"
    try:
        res = requests.get(url, params={"ids": "aptos", "vs_currencies": "usd"}, timeout=5)
        return res.json()["aptos"]["usd"]
    except Exception as e:
        print("❌ Ошибка получения цены APT:", e)
        return None

async def main():
    rest_client = RestClient(NODE_URL)

    direction = input("Выберите направление обмена (1 = APT → USDC, 2 = USDC → APT): ").strip()
    if direction not in ["1", "2"]:
        print("❌ Неверный выбор.")
        return

    apt_price = get_apt_price_usd()
    if not apt_price:
        return
    print(f"📊 Текущая цена APT: ${apt_price:.4f}")

    try:
        amount = float(input("Введите сумму для обмена: "))
    except ValueError:
        print("❌ Неверный ввод.")
        return

    if direction == "1":
        # APT → USDC
        amount_in = int(amount * 1e8)
        expected_usdc = amount * apt_price
        min_amount_out = int(expected_usdc * (1 - SLIPPAGE) * 1e6)
        type_tags = [
            TypeTag(StructTag.from_str(APT)),
            TypeTag(StructTag.from_str(USDC)),
            TypeTag(StructTag.from_str(CURVE)),
            TypeTag(StructTag.from_str(BINSTEP)),
        ]
        is_stable = [False]
        print(f"🔄 APT → USDC: минимум к получению {min_amount_out / 1e6:.4f} USDC")

    else:
        # USDC → APT
        amount_in = int(amount * 1e6)
        expected_apt = amount / apt_price
        min_amount_out = int(expected_apt * (1 - SLIPPAGE) * 1e8)
        type_tags = [
            TypeTag(StructTag.from_str(USDC)),
            TypeTag(StructTag.from_str(APT)),
            TypeTag(StructTag.from_str(CURVE)),
            TypeTag(StructTag.from_str(BINSTEP)),
        ]
        is_stable = [True]
        print(f"🔄 USDC → APT: минимум к получению {min_amount_out / 1e8:.6f} APT")

    entry_function = EntryFunction.natural(
        MODULE,
        FUNCTION,
        type_tags,
        [
            TransactionArgument(amount_in, Serializer.u64),
            TransactionArgument([min_amount_out], Serializer.sequence_serializer(Serializer.u64)),
            TransactionArgument(STEP_INDEX, Serializer.sequence_serializer(Serializer.u8)),
            TransactionArgument(is_stable, Serializer.sequence_serializer(Serializer.bool)),
        ]
    )

    payload = TransactionPayload(entry_function)

    signed_txn = await rest_client.create_bcs_signed_transaction(account, payload)
    print("🔐 Транзакция подписана")

    tx_hash = await rest_client.submit_bcs_transaction(signed_txn)
    print(f"🚀 Транзакция отправлена: {tx_hash}")

    await rest_client.close()

asyncio.run(main())
