#!/bin/sh

SCRIPT_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
PACKAGE_ROOT="$(cd "${SCRIPT_DIR}/.." 2>/dev/null && pwd)"
APP_NAME="${TRIM_APPNAME:-icloud-sync}"
DEFAULT_SYNC_ROOT="/var/apps/${APP_NAME}/shares/icloud"
LEGACY_SYNC_ROOT="/var/apps/${APP_NAME}/shares/icloud-photos"
WIZARD_CONFIG_FILE="${PACKAGE_ROOT}/wizard/config"
STORAGE_DIR="${TRIM_PKGVAR:-${PACKAGE_ROOT}/var}/config"
STORAGE_FILE="${STORAGE_DIR}/storage_root.json"
ACCESSIBLE_PATHS=""

json_escape() {
    printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

trim_text() {
    printf '%s' "$1" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//'
}

append_accessible_path() {
    candidate="$1"
    path=""

    if [ -z "$candidate" ] || [ "$candidate" = "$DEFAULT_SYNC_ROOT" ] || [ "$candidate" = "$LEGACY_SYNC_ROOT" ]; then
        return
    fi

    if [ -n "$ACCESSIBLE_PATHS" ]; then
        while IFS= read -r path; do
            if [ "$path" = "$candidate" ]; then
                return
            fi
        done <<EOF
$ACCESSIBLE_PATHS
EOF
        ACCESSIBLE_PATHS="${ACCESSIBLE_PATHS}
${candidate}"
    else
        ACCESSIBLE_PATHS="$candidate"
    fi
}

load_accessible_paths() {
    raw="${TRIM_DATA_ACCESSIBLE_PATHS:-}"
    candidate=""

    ACCESSIBLE_PATHS=""
    while [ -n "$raw" ]; do
        candidate="${raw%%:*}"
        if [ "$candidate" = "$raw" ]; then
            raw=""
        else
            raw="${raw#*:}"
        fi
        candidate="$(trim_text "$candidate")"
        append_accessible_path "$candidate"
    done
}

accessible_path_count() {
    if [ -z "$ACCESSIBLE_PATHS" ]; then
        printf '0'
    else
        printf '%s\n' "$ACCESSIBLE_PATHS" | awk 'END { print NR }'
    fi
}

current_selected_root() {
    if [ -n "${wizard_sync_root_path:-}" ]; then
        printf '%s' "$wizard_sync_root_path"
        return
    fi

    if [ -f "${STORAGE_FILE}" ]; then
        awk -F '"' '/"selected_root_path"/ { print $4; exit }' "${STORAGE_FILE}"
    fi
}

path_is_accessible() {
    candidate="$1"
    path=""

    if [ -z "$ACCESSIBLE_PATHS" ]; then
        return 1
    fi

    while IFS= read -r path; do
        if [ "$path" = "$candidate" ]; then
            return 0
        fi
    done <<EOF
$ACCESSIBLE_PATHS
EOF
    return 1
}

normalize_selected_root() {
    candidate="$1"

    if [ -z "$candidate" ] || [ "$candidate" = "$DEFAULT_SYNC_ROOT" ] || [ "$candidate" = "$LEGACY_SYNC_ROOT" ]; then
        printf '%s' "$DEFAULT_SYNC_ROOT"
        return
    fi

    if path_is_accessible "$candidate"; then
        printf '%s' "$candidate"
    elif [ "$(accessible_path_count)" -eq 0 ] && [ "${candidate#/}" != "$candidate" ]; then
        printf '%s' "$candidate"
    else
        printf '%s' "$DEFAULT_SYNC_ROOT"
    fi
}

write_storage_root_json() {
    selected_root="$1"
    using_default="false"
    path=""
    first=1

    if [ "$selected_root" = "$DEFAULT_SYNC_ROOT" ]; then
        using_default="true"
    fi

    mkdir -p "${STORAGE_DIR}" 2>/dev/null || return 0

    {
        printf '{\n'
        printf '  "selected_root_path": "%s",\n' "$(json_escape "$selected_root")"
        printf '  "using_default_root": %s,\n' "$using_default"
        printf '  "authorized_paths": [\n'
        if [ -n "$ACCESSIBLE_PATHS" ]; then
            while IFS= read -r path; do
                if [ "$first" -eq 0 ]; then
                    printf ',\n'
                fi
                printf '    "%s"' "$(json_escape "$path")"
                first=0
            done <<EOF
$ACCESSIBLE_PATHS
EOF
            printf '\n'
        fi
        printf '  ],\n'
        printf '  "updated_at": "%s"\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
        printf '}\n'
    } > "${STORAGE_FILE}" 2>/dev/null || true
}

write_wizard_config() {
    selected_root="$1"
    path=""
    help_text=""
    access_text=""
    wizard_dir=""
    path_count=0

    wizard_dir="$(dirname "${WIZARD_CONFIG_FILE}")"
    if [ ! -d "$wizard_dir" ]; then
        return 0
    fi
    if [ -e "${WIZARD_CONFIG_FILE}" ] && [ ! -w "${WIZARD_CONFIG_FILE}" ]; then
        return 0
    fi
    if [ ! -e "${WIZARD_CONFIG_FILE}" ] && [ ! -w "$wizard_dir" ]; then
        return 0
    fi

    path_count="$(accessible_path_count)"
    if [ "$path_count" -gt 0 ]; then
        help_text="你可以把同步根目录切换到飞牛里已授权的任意目录。保存后请重启应用，让容器重新挂载新的目录。"
        access_text="已检测到 ${path_count} 个已授权目录，可直接在下拉框中选择。"
    else
        help_text="当前还没有可用的授权目录，应用会继续使用默认共享目录。若要改为任意目录，请先在当前应用设置页为本应用授权目录，然后重新打开设置。"
        access_text="当前未检测到授权目录，暂时只能使用默认共享目录。"
    fi

    {
        printf '[\n'
        printf '  {\n'
        printf '    "stepTitle": "存储位置",\n'
        printf '    "items": [\n'
        printf '      {\n'
        printf '        "type": "tips",\n'
        printf '        "helpText": "%s"\n' "$(json_escape "$help_text")"
        printf '      },\n'
        printf '      {\n'
        printf '        "type": "tips",\n'
        printf '        "helpText": "%s"\n' "$(json_escape "$access_text")"
        printf '      },\n'
        printf '      {\n'
        printf '        "type": "select",\n'
        printf '        "field": "wizard_sync_root_path",\n'
        printf '        "label": "同步根目录",\n'
        printf '        "initValue": "%s",\n' "$(json_escape "$selected_root")"
        printf '        "options": [\n'
        printf '          { "label": "%s", "value": "%s" }' "$(json_escape "应用共享目录（默认）")" "$(json_escape "$DEFAULT_SYNC_ROOT")"
        if [ -n "$ACCESSIBLE_PATHS" ]; then
            while IFS= read -r path; do
                printf ',\n'
                printf '          { "label": "%s", "value": "%s" }' "$(json_escape "授权目录：$path")" "$(json_escape "$path")"
            done <<EOF
$ACCESSIBLE_PATHS
EOF
        fi
        printf '\n'
        printf '        ],\n'
        printf '        "rules": [\n'
        printf '          {\n'
        printf '            "required": true,\n'
        printf '            "message": "请选择同步根目录"\n'
        printf '          }\n'
        printf '        ]\n'
        printf '      }\n'
        printf '    ]\n'
        printf '  },\n'
        printf '  {\n'
        printf '    "stepTitle": "入口配置",\n'
        printf '    "items": [\n'
        printf '      {\n'
        printf '        "type": "tips",\n'
        printf '        "helpText": "%s"\n' "$(json_escape "详细同步选项请打开桌面图标进入 Web 面板设置。若修改了同步根目录，请保存后重启应用，让容器重新挂载新的目录。")"
        printf '      }\n'
        printf '    ]\n'
        printf '  }\n'
        printf ']\n'
    } > "${WIZARD_CONFIG_FILE}" 2>/dev/null || true
}
