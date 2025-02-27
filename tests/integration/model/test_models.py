"""Test API.

Tests the models using API. The weight paths from the trained models are used for the rest of the tests.
"""

# Copyright (C) 2023-2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0


from pathlib import Path

import pytest

from anomalib import TaskType
from anomalib.callbacks import ModelCheckpoint
from anomalib.data import AnomalibDataModule, MVTec, UCSDped
from anomalib.deploy.export import ExportType
from anomalib.engine import Engine
from anomalib.models import AnomalyModule, get_available_models, get_model


def models() -> list[str]:
    """Return all available models."""
    return get_available_models()


def export_types() -> list[ExportType]:
    """Return all available export frameworks."""
    return list(ExportType)


class TestAPI:
    """Do sanity check on all models."""

    @pytest.mark.parametrize("model_name", models())
    def test_fit(self, model_name: str, dataset_path: Path, project_path: Path) -> None:
        """Fit the model and save checkpoint.

        Args:
            model_name (str): Name of the model.
            dataset_path (Path): Root to dataset from fixture.
            project_path (Path): Path to temporary project folder from fixture.
        """
        model, dataset, engine = self._get_objects(
            model_name=model_name,
            dataset_path=dataset_path,
            project_path=project_path,
        )
        engine.fit(model=model, datamodule=dataset)

    @pytest.mark.parametrize("model_name", models())
    def test_test(self, model_name: str, dataset_path: Path, project_path: Path) -> None:
        """Test model from checkpoint.

        Args:
            model_name (str): Name of the model.
            dataset_path (Path): Root to dataset from fixture.
            project_path (Path): Path to temporary project folder from fixture.
        """
        model, dataset, engine = self._get_objects(
            model_name=model_name,
            dataset_path=dataset_path,
            project_path=project_path,
        )
        engine.test(model=model, datamodule=dataset, ckpt_path=f"{project_path}/{model_name}/dummy/weights/last.ckpt")

    @pytest.mark.parametrize("model_name", models())
    def test_train(self, model_name: str, dataset_path: Path, project_path: Path) -> None:
        """Train model from checkpoint.

        Args:
            model_name (str): Name of the model.
            dataset_path (Path): Root to dataset from fixture.
            project_path (Path): Path to temporary project folder from fixture.
        """
        model, dataset, engine = self._get_objects(
            model_name=model_name,
            dataset_path=dataset_path,
            project_path=project_path,
        )
        engine.train(model=model, datamodule=dataset, ckpt_path=f"{project_path}/{model_name}/dummy/weights/last.ckpt")

    @pytest.mark.parametrize("model_name", models())
    def test_validate(self, model_name: str, dataset_path: Path, project_path: Path) -> None:
        """Validate model from checkpoint.

        Args:
            model_name (str): Name of the model.
            dataset_path (Path): Root to dataset from fixture.
            project_path (Path): Path to temporary project folder from fixture.
        """
        model, dataset, engine = self._get_objects(
            model_name=model_name,
            dataset_path=dataset_path,
            project_path=project_path,
        )
        engine.validate(
            model=model,
            datamodule=dataset,
            ckpt_path=f"{project_path}/{model_name}/dummy/weights/last.ckpt",
        )

    @pytest.mark.parametrize("model_name", models())
    def test_predict(self, model_name: str, dataset_path: Path, project_path: Path) -> None:
        """Predict using model from checkpoint.

        Args:
            model_name (str): Name of the model.
            dataset_path (Path): Root to dataset from fixture.
            project_path (Path): Path to temporary project folder from fixture.
        """
        model, datamodule, engine = self._get_objects(
            model_name=model_name,
            dataset_path=dataset_path,
            project_path=project_path,
        )
        engine.predict(
            model=model,
            ckpt_path=f"{project_path}/{model_name}/dummy/weights/last.ckpt",
            datamodule=datamodule,
        )

    @pytest.mark.parametrize("model_name", models())
    @pytest.mark.parametrize("export_type", export_types())
    def test_export(
        self,
        model_name: str,
        export_type: ExportType,
        dataset_path: Path,
        project_path: Path,
    ) -> None:
        """Export model from checkpoint.

        Args:
            model_name (str): Name of the model.
            export_type (ExportType): Framework to export to.
            dataset_path (Path): Root to dataset from fixture.
            project_path (Path): Path to temporary project folder from fixture.
        """
        input_size = (256, 256)
        if model_name == "reverse_distillation":
            # TODO(ashwinvaidya17): Restore this test after fixing reverse distillation
            # https://github.com/openvinotoolkit/anomalib/issues/1513
            pytest.skip("Reverse distillation fails to convert to ONNX")
        elif model_name == "ai_vad":
            pytest.skip("Export fails for video models.")
        elif model_name == "win_clip":
            input_size = (240, 240)
        elif model_name == "uflow":
            input_size = (448, 448)

        model, dataset, engine = self._get_objects(
            model_name=model_name,
            dataset_path=dataset_path,
            project_path=project_path,
        )
        engine.export(
            model=model,
            datamodule=dataset,
            ckpt_path=f"{project_path}/{model_name}/dummy/weights/last.ckpt",
            export_type=export_type,
            input_size=input_size,
        )

    def _get_objects(
        self,
        model_name: str,
        dataset_path: Path,
        project_path: Path,
    ) -> tuple[AnomalyModule, AnomalibDataModule, Engine]:
        """Return model, dataset, and engine objects.

        Args:
            model_name (str): Name of the model to train
            dataset_path (Path): Path to the root of dummy dataset
            project_path (Path): path to the temporary project folder

        Returns:
            tuple[AnomalyModule, AnomalibDataModule, Engine]: Returns the created objects for model, dataset,
                and engine
        """
        # select task type
        if model_name in ("rkde", "ai_vad"):
            task_type = TaskType.DETECTION
        elif model_name in ("ganomaly", "dfkde"):
            task_type = TaskType.CLASSIFICATION
        else:
            task_type = TaskType.SEGMENTATION

        # set extra model args
        # TODO(ashwinvaidya17): Fix these Edge cases
        # https://github.com/openvinotoolkit/anomalib/issues/1478

        extra_args = {}
        if model_name == "patchcore":
            extra_args["input_size"] = (256, 256)
        elif model_name in ("rkde", "dfkde"):
            extra_args["n_pca_components"] = 2

        # select dataset
        if model_name == "ai_vad":
            # aivad expects UCSD dataset
            dataset = UCSDped(root=dataset_path / "ucsdped", category="dummy", task=task_type)
        elif model_name == "win_clip":
            dataset = MVTec(root=dataset_path / "mvtec", category="dummy", image_size=240, task=task_type)
        else:
            # EfficientAd requires that the batch size be lesser than the number of images in the dataset.
            # This is so that the LR step size is not 0.
            image_size = (448, 448) if model_name == "uflow" else (256, 256)
            dataset = MVTec(
                root=dataset_path / "mvtec",
                category="dummy",
                task=task_type,
                train_batch_size=2,
                image_size=image_size,
            )

        model = get_model(model_name, **extra_args)
        engine = Engine(
            logger=False,
            default_root_dir=project_path,
            max_epochs=1,
            devices=1,
            pixel_metrics=["F1Score", "AUROC"],
            task=task_type,
            callbacks=[
                ModelCheckpoint(
                    dirpath=f"{project_path}/{model_name}/dummy/weights",
                    monitor=None,
                    filename="last",
                    save_last=True,
                    auto_insert_metric_name=False,
                ),
            ],
            # TODO(ashwinvaidya17): Fix these Edge cases
            # https://github.com/openvinotoolkit/anomalib/issues/1478
            max_steps=70000 if model_name == "efficient_ad" else -1,
        )
        return model, dataset, engine
