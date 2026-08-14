import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_JAR = ROOT / 'sounds-2.5.1+edge+26.2-fabric-sources.jar'
JAVA_ROOT = ROOT / 'src' / 'client' / 'java' / 'com' / 'markuskjosen' / 'inventorysounds'
RES_ROOT = ROOT / 'src' / 'client' / 'resources'

if not SOURCE_JAR.exists():
    raise SystemExit(f'Missing source JAR: {SOURCE_JAR}')

if (ROOT / 'src').exists():
    shutil.rmtree(ROOT / 'src')
JAVA_ROOT.mkdir(parents=True, exist_ok=True)
(JAVA_ROOT / 'mixin').mkdir(parents=True, exist_ok=True)
RES_ROOT.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(SOURCE_JAR) as z:
    item_rules = []
    block_rules = []
    for name in z.namelist():
        if name.startswith('assets/minecraft/sounds/items/') and name.endswith('.json'):
            d = json.loads(z.read(name))
            for key in d['keys']:
                item_rules.append((key, d['soundEvent'], d.get('pitch'), d.get('volume')))
        elif name.startswith('assets/minecraft/sounds/blocks/') and name.endswith('.json'):
            d = json.loads(z.read(name)); g = d['group']
            for key in d['keys']:
                block_rules.append((key, g.get('place', {}).get('sound_id'), g.get('pitch'), g.get('volume')))

    def jf(v):
        return 'Float.NaN' if v is None else f'{float(v)}f'

    lines = [
        'package com.markuskjosen.inventorysounds;', '',
        'import java.util.List;',
        'import net.minecraft.client.Minecraft;',
        'import net.minecraft.client.resources.sounds.SimpleSoundInstance;',
        'import net.minecraft.client.resources.sounds.SoundInstance;',
        'import net.minecraft.core.registries.BuiltInRegistries;',
        'import net.minecraft.resources.Identifier;',
        'import net.minecraft.sounds.SoundSource;',
        'import net.minecraft.world.item.BlockItem;',
        'import net.minecraft.world.item.ItemStack;',
        'import net.minecraft.world.level.block.Block;', '',
        'public final class SoundRules {',
        '    public enum Kind { CLICK, DRAG, COPY }',
        '    private record ItemRule(String key, String sound, float pitch, float volume) {}',
        '    private record BlockRule(String key, String place, float pitch, float volume) {}', '',
        '    private static final List<ItemRule> ITEM_RULES = List.of('
    ]
    for i, (key, sound, pitch, volume) in enumerate(sorted(item_rules)):
        comma = ',' if i < len(item_rules) - 1 else ''
        lines.append(f'        new ItemRule("{key}", "{sound}", {jf(pitch)}, {jf(volume)}){comma}')
    lines += ['    );', '', '    private static final List<BlockRule> BLOCK_RULES = List.of(']
    for i, (key, place, pitch, volume) in enumerate(sorted(block_rules)):
        comma = ',' if i < len(block_rules) - 1 else ''
        place_java = 'null' if place is None else f'"{place}"'
        lines.append(f'        new BlockRule("{key}", {place_java}, {jf(pitch)}, {jf(volume)}){comma}')
    lines += [
        '    );', '', '    private SoundRules() {}', '',
        '    public static void play(ItemStack stack, Kind kind) {',
        '        String sound = kind == Kind.COPY ? "sounds:ui.inventory.copy" : "sounds:ui.inventory.pick";',
        '        float pitch = kind == Kind.DRAG ? 1.6f : 2.0f;',
        '        float volume = kind == Kind.COPY ? 0.2f : 0.4f;', '',
        '        if (!stack.isEmpty()) {',
        '            if (stack.getItem() instanceof BlockItem blockItem) {',
        '                Block block = blockItem.getBlock();',
        '                String blockId = BuiltInRegistries.BLOCK.getKey(block).toString();',
        '                BlockRule br = findBlockRule(block, blockId);',
        '                if (br != null && br.place != null) {',
        '                    sound = br.place;',
        '                    if (!Float.isNaN(br.pitch)) pitch = br.pitch;',
        '                    if (!Float.isNaN(br.volume)) volume = br.volume;',
        '                } else {',
        '                    sound = block.defaultBlockState().getSoundType().getPlaceSound().location().toString();',
        '                }',
        '            }', '',
        '            String itemId = BuiltInRegistries.ITEM.getKey(stack.getItem()).toString();',
        '            ItemRule ir = findItemRule(stack, itemId);',
        '            if (ir != null) {',
        '                sound = ir.sound;',
        '                if (!Float.isNaN(ir.pitch)) pitch = ir.pitch;',
        '                if (!Float.isNaN(ir.volume)) volume = ir.volume;',
        '            }',
        '        }', '',
        '        Minecraft.getInstance().getSoundManager().play(new SimpleSoundInstance(',
        '                Identifier.parse(sound), SoundSource.UI, volume, pitch, SoundInstance.createUnseededRandom(),',
        '                false, 0, SoundInstance.Attenuation.NONE, 0.0, 0.0, 0.0, true));',
        '    }', '',
        '    private static ItemRule findItemRule(ItemStack stack, String itemId) {',
        '        for (ItemRule rule : ITEM_RULES) {',
        '            if (!rule.key.startsWith("#") && rule.key.equals(itemId)) return rule;',
        '            if (rule.key.startsWith("#")) {',
        '                String tag = rule.key.substring(1);',
        '                if (stack.tags().anyMatch(t -> t.location().toString().equals(tag))) return rule;',
        '            }',
        '        }',
        '        return null;',
        '    }', '',
        '    private static BlockRule findBlockRule(Block block, String blockId) {',
        '        for (BlockRule rule : BLOCK_RULES) {',
        '            if (!rule.key.startsWith("#") && rule.key.equals(blockId)) return rule;',
        '            if (rule.key.startsWith("#")) {',
        '                String tag = rule.key.substring(1);',
        '                if (block.defaultBlockState().getTags().anyMatch(t -> t.location().toString().equals(tag))) return rule;',
        '            }',
        '        }',
        '        return null;',
        '    }',
        '}'
    ]
    (JAVA_ROOT / 'SoundRules.java').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    (JAVA_ROOT / 'InventorySoundsClient.java').write_text('''package com.markuskjosen.inventorysounds;\n\nimport net.fabricmc.api.ClientModInitializer;\n\npublic final class InventorySoundsClient implements ClientModInitializer {\n    @Override public void onInitializeClient() {}\n}\n''', encoding='utf-8')

    (JAVA_ROOT / 'mixin' / 'ItemTransferMixin.java').write_text('''package com.markuskjosen.inventorysounds.mixin;\n\nimport com.markuskjosen.inventorysounds.SoundRules;\nimport net.minecraft.client.player.LocalPlayer;\nimport net.minecraft.world.entity.player.Player;\nimport net.minecraft.world.inventory.AbstractContainerMenu;\nimport net.minecraft.world.inventory.ContainerInput;\nimport net.minecraft.world.inventory.Slot;\nimport net.minecraft.world.item.ItemStack;\nimport org.spongepowered.asm.mixin.Mixin;\nimport org.spongepowered.asm.mixin.Shadow;\nimport org.spongepowered.asm.mixin.injection.At;\nimport org.spongepowered.asm.mixin.injection.Inject;\nimport org.spongepowered.asm.mixin.injection.callback.CallbackInfo;\n\n@Mixin(AbstractContainerMenu.class)\npublic abstract class ItemTransferMixin {\n    @Shadow public abstract Slot getSlot(int index);\n    @Shadow public abstract ItemStack getCarried();\n\n    @Inject(method = "doClick", at = @At("HEAD"))\n    private void inventorysounds$playTransfer(int slotIndex, int button, ContainerInput actionType, Player player, CallbackInfo ci) {\n        if (!(player instanceof LocalPlayer) || slotIndex < 0) return;\n        ItemStack slotStack = getSlot(slotIndex).getItem();\n        ItemStack soundStack = slotStack;\n        if (actionType == ContainerInput.PICKUP || actionType == ContainerInput.PICKUP_ALL || actionType == ContainerInput.QUICK_MOVE) {\n            if (slotStack.isEmpty()) soundStack = getCarried();\n            SoundRules.play(soundStack, SoundRules.Kind.CLICK);\n        } else if (actionType == ContainerInput.SWAP) {\n            if (slotStack.isEmpty()) soundStack = player.getInventory().getItem(button);\n            SoundRules.play(soundStack, SoundRules.Kind.CLICK);\n        } else if (actionType == ContainerInput.CLONE) {\n            SoundRules.play(slotStack, SoundRules.Kind.COPY);\n        }\n    }\n}\n''', encoding='utf-8')

    (JAVA_ROOT / 'mixin' / 'ItemDragMixin.java').write_text('''package com.markuskjosen.inventorysounds.mixin;\n\nimport com.llamalad7.mixinextras.sugar.Local;\nimport com.markuskjosen.inventorysounds.SoundRules;\nimport net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;\nimport net.minecraft.client.input.MouseButtonEvent;\nimport net.minecraft.world.inventory.AbstractContainerMenu;\nimport net.minecraft.world.inventory.Slot;\nimport org.spongepowered.asm.mixin.Final;\nimport org.spongepowered.asm.mixin.Mixin;\nimport org.spongepowered.asm.mixin.Shadow;\nimport org.spongepowered.asm.mixin.injection.At;\nimport org.spongepowered.asm.mixin.injection.Inject;\nimport org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;\nimport java.util.Set;\n\n@Mixin(AbstractContainerScreen.class)\npublic abstract class ItemDragMixin<T extends AbstractContainerMenu> {\n    @Shadow @Final protected Set<Slot> quickCraftSlots;\n    @Shadow @Final protected T menu;\n\n    @Inject(method = "mouseDragged", at = @At(value = "INVOKE", target = "Ljava/util/Set;add(Ljava/lang/Object;)Z"))\n    private void inventorysounds$playDrag(MouseButtonEvent event, double x, double y, CallbackInfoReturnable<Boolean> cir, @Local Slot slot) {\n        if (!quickCraftSlots.contains(slot) && !quickCraftSlots.isEmpty()) {\n            SoundRules.play(menu.getCarried(), SoundRules.Kind.DRAG);\n        }\n    }\n}\n''', encoding='utf-8')

    (RES_ROOT / 'inventorysounds.mixins.json').write_text(json.dumps({
        'required': True,
        'minVersion': '0.8',
        'package': 'com.markuskjosen.inventorysounds.mixin',
        'compatibilityLevel': 'JAVA_21',
        'client': ['ItemTransferMixin', 'ItemDragMixin'],
        'injectors': {'defaultRequire': 1}
    }, indent=2) + '\n', encoding='utf-8')

    (RES_ROOT / 'fabric.mod.json').write_text('''{\n  "schemaVersion": 1,\n  "id": "inventorysounds",\n  "version": "${version}",\n  "name": "Inventory Sounds",\n  "description": "Client-side inventory item movement sounds only.",\n  "authors": ["markuskjosen"],\n  "environment": "client",\n  "entrypoints": {"client": ["com.markuskjosen.inventorysounds.InventorySoundsClient"]},\n  "mixins": ["inventorysounds.mixins.json"],\n  "depends": {"fabricloader": ">=0.19.3", "minecraft": "26.2", "java": ">=25"}\n}\n''', encoding='utf-8')

    sounds = json.loads(z.read('assets/sounds/sounds.json'))
    targets = {'ui.inventory.pick', 'ui.inventory.copy'}
    for _, sound, _, _ in item_rules:
        if sound.startswith('sounds:'): targets.add(sound.split(':', 1)[1])
    for _, place, _, _ in block_rules:
        if place and place.startswith('sounds:'): targets.add(place.split(':', 1)[1])

    selected, files, queue, seen = {}, set(), list(targets), set()
    while queue:
        event = queue.pop()
        if event in seen: continue
        seen.add(event)
        definition = sounds.get(event)
        if definition is None: continue
        selected[event] = definition
        for entry in definition.get('sounds', []):
            if isinstance(entry, str): name, typ = entry, 'file'
            else: name, typ = entry.get('name', ''), entry.get('type', 'file')
            if typ == 'event':
                if ':' in name:
                    ns, path = name.split(':', 1)
                    if ns == 'sounds': queue.append(path)
                else: queue.append(name)
            else:
                if ':' in name:
                    ns, path = name.split(':', 1)
                    if ns != 'sounds': continue
                else: path = name
                files.add(f'assets/sounds/sounds/{path}.ogg')

    asset_root = RES_ROOT / 'assets' / 'sounds'
    (asset_root / 'sounds').mkdir(parents=True, exist_ok=True)
    (asset_root / 'sounds.json').write_text(json.dumps(selected, indent=2) + '\n', encoding='utf-8')
    copied = 0
    for member in sorted(files):
        try: data = z.read(member)
        except KeyError: continue
        dest = RES_ROOT / member
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data); copied += 1

print(f'Generated standalone sources: {len(item_rules)} item rules, {len(block_rules)} block rules, {len(selected)} sound events, {copied} bundled audio files.')
