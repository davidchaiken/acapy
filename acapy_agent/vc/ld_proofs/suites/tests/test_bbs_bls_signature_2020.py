from unittest import IsolatedAsyncioTestCase, mock

import pytest

from .....did.did_key import DIDKey
from .....utils.testing import create_test_profile
from .....wallet.base import BaseWallet
from .....wallet.key_type import BLS12381G2
from ....tests.data import (
    TEST_LD_DOCUMENT,
    TEST_LD_DOCUMENT_BAD_SIGNED_BBS,
    TEST_LD_DOCUMENT_SIGNED_BBS,
    TEST_VC_DOCUMENT,
    TEST_VC_DOCUMENT_SIGNED_BBS,
)
from ....tests.document_loader import custom_document_loader
from ...crypto.wallet_key_pair import WalletKeyPair
from ...error import LinkedDataProofException
from ...ld_proofs import sign, verify
from ...purposes.assertion_proof_purpose import AssertionProofPurpose
from ..bbs_bls_signature_2020 import BbsBlsSignature2020


@pytest.mark.ursa_bbs_signatures
class TestBbsBlsSignature2020(IsolatedAsyncioTestCase):
    test_seed = "testseed000000000000000000000001"

    async def asyncSetUp(self):
        self.profile = await create_test_profile()
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            self.key = await wallet.create_signing_key(
                key_type=BLS12381G2, seed=self.test_seed
            )
        self.verification_method = DIDKey.from_public_key_b58(
            self.key.verkey, BLS12381G2
        ).key_id

        self.sign_key_pair = WalletKeyPair(
            profile=self.profile,
            key_type=BLS12381G2,
            public_key_base58=self.key.verkey,
        )
        self.verify_key_pair = WalletKeyPair(profile=self.profile, key_type=BLS12381G2)

    async def test_sign_ld_proofs(self):
        signed = await sign(
            document=TEST_LD_DOCUMENT,
            suite=BbsBlsSignature2020(
                key_pair=self.sign_key_pair,
                verification_method=self.verification_method,
            ),
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert signed

    async def test_verify_ld_proofs(self):
        result = await verify(
            document=TEST_LD_DOCUMENT_SIGNED_BBS,
            suites=[BbsBlsSignature2020(key_pair=self.verify_key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert result
        assert result.verified

    async def test_verify_ld_proofs_not_verified_bad_signature(self):
        result = await verify(
            document=TEST_LD_DOCUMENT_BAD_SIGNED_BBS,
            suites=[BbsBlsSignature2020(key_pair=self.verify_key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert result
        assert not result.verified

    async def test_verify_ld_proofs_not_verified_unsigned_statement(self):
        MODIFIED_DOCUMENT = {**TEST_LD_DOCUMENT_SIGNED_BBS, "unsigned_claim": "oops"}
        result = await verify(
            document=MODIFIED_DOCUMENT,
            suites=[BbsBlsSignature2020(key_pair=self.verify_key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert result
        assert not result.verified

    async def test_verify_ld_proofs_not_verified_changed_statement(self):
        MODIFIED_DOCUMENT = {
            **TEST_LD_DOCUMENT_SIGNED_BBS,
            "email": "someOtherEmail@example.com",
        }
        result = await verify(
            document=MODIFIED_DOCUMENT,
            suites=[BbsBlsSignature2020(key_pair=self.verify_key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert result
        assert not result.verified

    async def test_sign_vc(self):
        signed = await sign(
            document=TEST_VC_DOCUMENT,
            suite=BbsBlsSignature2020(
                key_pair=self.sign_key_pair,
                verification_method=self.verification_method,
            ),
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert signed

    async def test_verify_vc(self):
        result = await verify(
            document=TEST_VC_DOCUMENT_SIGNED_BBS,
            suites=[BbsBlsSignature2020(key_pair=self.verify_key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert result
        assert result.verified

    async def test_verify_signature_x_invalid_proof_value(self):
        suite = BbsBlsSignature2020(
            key_pair=self.sign_key_pair,
            verification_method=self.verification_method,
        )

        with self.assertRaises(LinkedDataProofException):
            await suite.verify_signature(
                verify_data=mock.MagicMock(),
                verification_method=mock.MagicMock(),
                document=mock.MagicMock(),
                proof={"proofValue": {"not": "a string"}},
                document_loader=mock.MagicMock(),
            )
