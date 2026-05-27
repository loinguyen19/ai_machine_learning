from pathlib import Path

from app.generation.pipeline import GenerationPipeline


class FakeAssembler:
    def assemble(self, duration_sec: int, output_path: Path) -> None:
        output_path.write_bytes(b"fake-mp4")


def test_pipeline_with_mocked_assembler(tmp_path: Path) -> None:
    pipeline = GenerationPipeline(assembler=FakeAssembler())  # type: ignore[arg-type]
    output = tmp_path / "out.mp4"
    result = pipeline.run(
        query="How does the pH scale work?",
        work_dir=tmp_path,
        output_path=output,
    )
    assert output.exists()
    assert result["script"]["title"]
    assert result["duration_sec"] > 0
