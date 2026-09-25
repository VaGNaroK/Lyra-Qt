"""
Testes de validação estrutural do manifesto Flatpak e scripts de build.
Garante a conformidade com as regras do Flathub para o KDE Application Platform 6.11.
"""
import os
import re

MANIFEST_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "build_scripts", "com.github.vagnarok.lyra.yml")
)
AUTO_BUILD_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "build_scripts", "auto_build.sh")
)


def test_flatpak_manifest_exists():
    """Verifica se o manifesto existe no local esperado."""
    assert os.path.isfile(MANIFEST_PATH), f"Manifesto não encontrado em: {MANIFEST_PATH}"


def test_flatpak_manifest_kde_runtime_version():
    """
    Valida se o manifesto está configurado para a versão estável 6.11
    do KDE Application Platform e SDK, sem apontar para versões legadas/EOL.
    """
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # App ID
    assert re.search(r"^app-id:\s*com\.github\.vagnarok\.lyra", content, re.MULTILINE), \
        "app-id deve ser com.github.vagnarok.lyra"

    # Runtime
    assert re.search(r"^runtime:\s*org\.kde\.Platform", content, re.MULTILINE), \
        "runtime deve ser org.kde.Platform"

    # Runtime Version: deve ser estritamente '6.11'
    match_version = re.search(r"^runtime-version:\s*['\"]?([^'\"\n]+)['\"]?", content, re.MULTILINE)
    assert match_version is not None, "runtime-version não encontrado no manifesto"
    assert match_version.group(1).strip() == "6.11", \
        f"runtime-version esperado: '6.11', encontrado: '{match_version.group(1)}'"

    # SDK
    assert re.search(r"^sdk:\s*org\.kde\.Sdk", content, re.MULTILINE), \
        "sdk deve ser org.kde.Sdk"


def test_flatpak_manifest_no_legacy_ffmpeg_full():
    """
    🔒 FIX: No Freedesktop SDK 25.08 / KDE Platform 6.11, a extensão ffmpeg-full foi
    descontinuada e substituída por codecs-extra (gerenciada automaticamente pelo Flathub).
    Portanto, add-extensions não deve declarar ffmpeg-full:24.08.
    """
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert "ffmpeg-full" not in content, \
        "A extensão legada ffmpeg-full não deve estar presente no manifesto 6.11"
    assert "24.08" not in content, \
        "Referências ao Freedesktop SDK 24.08 não devem permanecer no manifesto 6.11"


def test_flatpak_manifest_essential_modules_and_permissions():
    """
    Garante que os módulos vitais (ffmpeg com nvenc, libmpv, python-dependencies, lyra-app)
    e permissões críticas de desktop/áudio estejam declarados.
    """
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Módulos vitais
    assert "name: ffmpeg" in content, "Módulo ffmpeg deve estar presente"
    assert "name: libmpv" in content, "Módulo libmpv deve estar presente"
    assert "name: python-dependencies" in content, "Módulo python-dependencies deve estar presente"
    assert "name: lyra-app" in content, "Módulo lyra-app deve estar presente"

    # Permissões essenciais (finish-args)
    assert "--socket=wayland" in content
    assert "--socket=pulseaudio" in content
    assert "--filesystem=xdg-run/pipewire-0" in content
    assert "--device=dri" in content
    assert "--env=QT_QPA_PLATFORM=xcb" in content


def test_auto_build_script_kde_versions():
    """
    Valida se o script auto_build.sh instala as dependências corretas (KDE Platform e SDK 6.11).
    """
    assert os.path.isfile(AUTO_BUILD_PATH), f"auto_build.sh não encontrado em: {AUTO_BUILD_PATH}"

    with open(AUTO_BUILD_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert "org.kde.Platform/x86_64/6.11" in content, \
        "auto_build.sh deve instalar org.kde.Platform/x86_64/6.11"
    assert "org.kde.Sdk/x86_64/6.11" in content, \
        "auto_build.sh deve instalar org.kde.Sdk/x86_64/6.11"
    assert "6.9" not in content, \
        "auto_build.sh não deve conter referências residuais à versão 6.9"
    assert "ffmpeg-full" not in content, \
        "auto_build.sh não deve tentar instalar a extensão legada ffmpeg-full"


def test_flatpak_manifest_ffmpeg_disable_doc():
    """
    🔒 FIX: Verifica se o módulo ffmpeg inclui '--disable-doc' para evitar
    falha de compilação com Texinfo 7.1+ (KDE SDK 6.11 / Freedesktop 25.08).
    """
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert "--disable-doc" in content, \
        "O módulo ffmpeg deve conter '--disable-doc' para evitar erro de build com texinfo"


def test_flatpak_manifest_libmpv_release_opts():
    """
    🔒 FIX: Verifica se o módulo libmpv inclui opções de build de release
    (-Dbuildtype=release, -Ddebug=false e -DNDEBUG) para evitar asserções de debug
    e falhas de alocação de memória no ta.c ao rodar sob o runtime do Flatpak.
    """
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert "-Dbuildtype=release" in content, \
        "O módulo libmpv deve conter '-Dbuildtype=release'"
    assert "-Ddebug=false" in content, \
        "O módulo libmpv deve conter '-Ddebug=false'"
    assert "-DNDEBUG" in content, \
        "O módulo libmpv deve conter '-DNDEBUG' em cflags"


def test_mpv_patch_contains_option_value_fix():
    """
    🔒 FIX: Verifica se o patch mpv-ffmpeg7.patch contém a correção para
    a inicialização incompleta de 'union m_option_value' em m_config_frontend.c,
    que causava aborto com código 134 (ta_dbg_check_header canary assertion).
    """
    patch_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "build_scripts", "mpv-ffmpeg7.patch")
    )
    assert os.path.isfile(patch_path), f"Patch não encontrado: {patch_path}"

    with open(patch_path, "r", encoding="utf-8") as f:
        patch_content = f.read()

    assert "union m_option_value" in patch_content, \
        "Patch deve conter a correção para union m_option_value"
    assert "memset(&val, 0, sizeof(val));" in patch_content, \
        "Patch deve inicializar explicitamente val com memset para prevenir lixo na stack"

