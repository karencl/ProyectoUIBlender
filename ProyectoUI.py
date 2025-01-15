bl_info = {
    "name": "Operadores para Artistas 3D",
    "author": "Karen Cebreros López",
    "version": (0, 0, 1),
    "blender": (4, 2, 3),
    "location": "3D View > Sidebar > Operadores Artistas 3D",
    "description": "Operadores útiles para artistas 3D",
    "category": "Development"
}

import bpy
import bmesh
from mathutils import Vector
from bpy.types import Menu


# Diccionario global para almacenar múltiples objetos
stored_objects = {}
# Lista global para los accesos directos
global_addon_keymaps = []


# --------------------------------------------------------------------------------
# Operador para mover un objeto del mundo usando el vértice más cercano al origen
# --------------------------------------------------------------------------------
class MESH_OT_move_object_to_world_origin(bpy.types.Operator):

    bl_idname = "object.move_object_to_world_origin"  
    bl_label = "Mover Objeto al Origen"
    bl_options = {"REGISTER", "UNDO"}   

    def execute(self, context):
        # Se obtiene el objeto activo
        obj = context.active_object

        # Se verifica si hay un objeto activo y si es del tipo mesh
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "El objeto activo no es del tipo mesh.")
            return {'CANCELLED'}
        
        # Se cambia al modo de edición,se obtienen los datos de la malla y con ellos se crea una estructura "bmesh" para manipular los vértices
        bpy.ops.object.mode_set(mode='EDIT')
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        
        # Inicializar variables para encontrar el vértice más cercano
        closest_vertex = None               # Posición global del vértice más cercano
        closest_distance = float('inf')     # Inicializar una distancia infinita para comparar después
        origin = Vector((0.0, 0.0, 0.0))    # Origen del mundo (0,0,0) como un vector 

        # Se recorren todos los vértices para encontrar el vértice más cercano al origen
        for vert in bm.verts:
            global_pos = obj.matrix_world @ vert.co     # Se saca posición global del objeto, usando la posición local del vértice y la matriz de transformación del objeto
            distance = (global_pos - origin).length     # Se calcula la distancia al origen
            
            # Si se cumple la condición, se guarda la posición y la distancia más cercana
            if distance < closest_distance:             
                closest_vertex = global_pos
                closest_distance = distance

        # Se cambia de nuevo al modo objeto
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Para evitar errores se verifica que se haya encontrado un vértice válido
        if closest_vertex:
            translation_vector = -closest_vertex    # Se calcula el vector de traslación usando la posicón global en negativo del vértice para después moverlo al origen
            obj.location += translation_vector      # Se desplaza el objeto al origen
        else:
            self.report({'WARNING'}, "No se encontraro un vértice válido.")
        
        return {'FINISHED'}


# -----------------------------------------------------------------------
# Operador para aplicar cierto número de cortes seleccionando una arista 
# -----------------------------------------------------------------------
class MESH_OT_cut_selected_object(bpy.types.Operator):

    bl_idname = "mesh.cut_selected_object"
    bl_label = "Cortar Objeto Seleccionado"
    bl_options = {"UNDO"}                       # Eliminé "REGISTER" para evitar que saliera el menú de selección de cortes nuevamente, una vez ya realizados los cortes

    # Preguntar número de cortes al usuario
    def invoke(self, context, event):
        # Se obtiene el objeto activo
        obj = context.active_object

        # Se verifica si hay un objeto activo y si es del tipo mesh
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "El objeto activo no es del tipo mesh.")
            return {'CANCELLED'}

        # Se guarda el contexto para el modal
        self.obj = obj

        # Se muestra cuadro de diálogo para preguntar el número de cortes antes de hacerlos
        context.window_manager.invoke_props_dialog(self)
        return {'RUNNING_MODAL'}

    # Menú para seleccionar el número de cortes
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "number_of_cuts", text="Número de Cortes")

    # Propiedad para el número de cortes (del 1 al 10). El rango del número de cortes se puede ajustar, pero por simplicidad yo lo dejé del 1 al 10
    number_of_cuts: bpy.props.IntProperty(
        name="Número de Cortes",
        default=1,
        min=1,
        max=10,
        description="Selecciona el número de cortes"
    )

    def execute(self, context):
        # Se cambia al modo de edición y se activa la selección de aristas
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='EDGE')

        # Instrucciones para el usuario
        self.report({'INFO'}, "Selecciona una arista y ajusta el corte.")
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        # Se espera a la selección del usuario
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            
            # Se verifica que haya al menos una arista seleccionada y que sea válida
            selected_edges = []
            for e in self.obj.data.edges:
                if e.select:
                    selected_edges.append(e)

            if not selected_edges:
                self.report({'WARNING'}, "Selecciona una arista válida.")
                return {'RUNNING_MODAL'}

            try:
                # Se aplica el operador de corte (que modifiqué para que fuera interactivo y se pudiera usar con modal())
                bpy.ops.mesh.loopcut_slide(
                    MESH_OT_loopcut={
                        "number_cuts": self.number_of_cuts,             # Número de cortes seleccionado anteriormente
                        "smoothness": 0,
                        "falloff": 'INVERSE_SQUARE',
                        "object_index": 0,
                        "edge_index": selected_edges[0].index,          # Índice de la arista seleccionada
                        "mesh_select_mode_init": (True, False, False)
                    }
                )
                
                # Se vuelve al modo objeto después de aplicar el/los corte(s). 
                # Línea comentada para poder ver los cortes que se hicieron con éxito
                # bpy.ops.object.mode_set(mode='OBJECT')

                self.report({'INFO'}, f"Se realizaron {self.number_of_cuts} cortes correctamente.")
                return {'FINISHED'}

            # Manejo de errores por si falla algo al aplicar el corte
            except RuntimeError as e:
                self.report({'ERROR'}, f"Error al aplicar el corte: {e}")
                return {'CANCELLED'}
        
        # Para salir del evento sin que se trabe el programa, se pueden usar el click derecho o esc para cancelar la operación
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.report({'INFO'}, "Corte cancelado.")
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}


# -------------------------------------------------------------------------
# Operador para guardar un objeto seleccionado con un nombre personalizado
# -------------------------------------------------------------------------
class MESH_OT_save_selected_object(bpy.types.Operator):
    
    bl_idname = "mesh.save_selected_object"
    bl_label = "Guardar Objeto Seleccionado"
    bl_options = {"UNDO"}

    # Propiedad para el nombre del objeto
    object_name: bpy.props.StringProperty(
        name="Nombre del Objeto",
        default="ObjetoGuardado"
    )
    
    # Preguntar nombre del objeto a guardar al usuario
    def invoke(self, context, event):
        # Se obtiene el objeto activo
        obj = context.active_object
        
        # Se verifica si hay algún objeto seleccionado
        if not obj:
            self.report({'WARNING'}, "No hay ningún objeto seleccionado.")
            return {'CANCELLED'}

        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        global stored_objects
        # Se obtiene el objeto activo
        obj = context.active_object

        # Verificar si ya existe un objeto con el mismo nombre en el diccionario
        if self.object_name in stored_objects:
            self.report({'WARNING'}, f"Ya existe un objeto guardado con el nombre '{self.object_name}'.")
            return {'CANCELLED'}

        # Guardar datos del objeto
        stored_objects[self.object_name] = {
            "mesh_data": obj.data.copy(),               # Datos de la malla
            "location": obj.location.copy(),            # Ubicación
            "rotation": obj.rotation_euler.copy(),      # Rotación de Euler
            "scale": obj.scale.copy()                   # Escala
        }

        self.report({'INFO'}, f"Objeto '{self.object_name}' guardado correctamente.")
        return {'FINISHED'}
    

# -----------------------------------------
# Operador para colocar un objeto guardado
# -----------------------------------------
class MESH_OT_place_saved_object(bpy.types.Operator):

    bl_idname = "mesh.place_saved_object"
    bl_label = "Colocar Objeto Guardado"
    bl_options = {"UNDO"}

    # Se obtiene la lista de objetos guardados
    def get_stored_objects(self, context):
        global stored_objects
        
        # Se revisa si hay al menos un objeto en la lista
        if not stored_objects:
            return [('NONE', "No hay objetos", "No hay objetos guardados")]

        # Si hay un objeto o más, se ejecuta esta parte del código donde se crea la lista de opciones de los objetos guardados para colocar
        stored_list = []

        # Se recorren todos los nombres de objetos guardados
        for name in stored_objects.keys():
            # Se crea la tupla con el formato requerido
            option = (name, name, f"Colocar {name}")
            
            # Y se agrega a la lista
            stored_list.append(option)

        # Se devuelve dicha lista
        return stored_list

    # Propiedad para seleccionar el objeto dentro de la lista de objetos guardados 
    selected_object: bpy.props.EnumProperty(
        name="Objetos Guardados",
        description="Selecciona el objeto a colocar",
        items=get_stored_objects
    )

    # Pedir al usuario que seleccione el objeto a colocar, dentro de la lista de objetos guardados
    def invoke(self, context, event):
        # Se verifica si hay al menos un objeto guardado
        if not stored_objects:
            self.report({'WARNING'}, "No hay objetos guardados.")
            return {'CANCELLED'}
        
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        global stored_objects

        # Cuidar que se se seleccione un objeto válido
        if self.selected_object == 'NONE':
            self.report({'WARNING'}, "Selecciona un objeto válido.")
            return {'CANCELLED'}

        # Se guardan los datos del objeto a colocar seleccionado
        obj_data = stored_objects[self.selected_object]

        # Se crea el nuevo objeto con los datos guardados
        new_obj = bpy.data.objects.new(self.selected_object, obj_data["mesh_data"])     # Datos de la malla
        new_obj.location = obj_data["location"]                                         # Ubicación
        new_obj.rotation_euler = obj_data["rotation"]                                   # Rotación de Euler
        new_obj.scale = obj_data["scale"]                                               # Escala

        # Se agrega el objeto
        context.collection.objects.link(new_obj)        
        context.view_layer.objects.active = new_obj     # Se pone como activo
        new_obj.select_set(True)                        # Se selecciona automáticamente

        self.report({'INFO'}, f"Objeto '{self.selected_object}' colocado en la escena.")
        return {'FINISHED'}
    

# ----------------------------------------------
# Operador para exportar un objeto seleccionado
# ----------------------------------------------
class MESH_OT_export_selected_object(bpy.types.Operator):
    
    bl_idname = "mesh.export_selected_object"
    bl_label = "Exportar Objeto Seleccionado"
    bl_options = {"UNDO"}

    # Propiedades del archivo (nombre y ruta completa de exportación)
    filepath: bpy.props.StringProperty(subtype="FILE_PATH", name="Ruta de Exportación")
    filename: bpy.props.StringProperty(name="Nombre del Archivo", default="exported_object")

    # Se le pide al usuario la ruta donde se desea exportar el archivo del objeto
    def invoke(self, context, event):
        # Se obtiene el objeto activo
        obj = context.active_object

        # Se verifica si hay un objeto activo y si es del tipo mesh
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No hay ningún objeto seleccionado o no es del tipo mesh.")
            return {'CANCELLED'}

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        # Se obtiene el objeto activo
        obj = context.active_object

        # Se verifica si hay un objeto activo y si es del tipo mesh
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No hay ningún objeto seleccionado o no es del tipo mesh.")
            return {'CANCELLED'}

        # Se asegura de que el solo objeto esté seleccionado para su exportación
        bpy.ops.object.select_all(action='DESELECT')    # Primero se desselecciona todo
        obj.select_set(True)                            # Luego se selecciona manualmente
        context.view_layer.objects.active = obj         # Y finalmente se configura como el objeto activo

        try:
            # Se exporta usando el operador de exportación de Blender para OBJ (esto para la versión 4.0 en adelante por lo que investigué)
            bpy.ops.wm.obj_export(
                filepath=f"{self.filepath}.obj"
            )

            self.report({'INFO'}, f"Object '{obj.name}' successfully exported to {self.filepath}.obj")
            return {'FINISHED'}

        except RuntimeError as e:
            self.report({'ERROR'}, f"Error al exportar: {e}")
            return {'CANCELLED'}


# ------------------------------
# Menú PIE para accesos rápidos
# ------------------------------
class VIEW3D_MT_PIE_template(Menu):
    
    bl_label = "Custom Pie Menu"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        # Operador: Mover un vértice de un objeto al origen
        pie.operator("object.move_object_to_world_origin", text="Objeto al origen", icon="EMPTY_SINGLE_ARROW")

        # Operador: Guardar objeto seleccionado
        pie.operator("mesh.save_selected_object", text="Guardar objeto", icon="COLLECTION_NEW")
        
        # Operador: Exportar objeto seleccionado
        pie.operator("mesh.export_selected_object", text="Exportar objeto", icon="BLENDER")


# --------------------------------------------------
# Panel de operadores personalizados en la vista 3D
# --------------------------------------------------
class ToolsPanel(bpy.types.Panel):
    
    bl_idname = "VIEW3D_PT_OperadoresArtistas3D"
    bl_label = "Operadores Artistas 3D"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Operadores Artistas 3D"

    def draw(self, context):
        layout = self.layout
        
        row = layout.row()
        row.label(text="Mover objeto al origen", icon="EMPTY_SINGLE_ARROW")
        
        row = layout.row()
        row.operator("object.move_object_to_world_origin")
        
        row = layout.row()
        row.label(text="Cortar objeto", icon="OUTLINER_OB_LATTICE")
        
        row = layout.row()
        row.operator("mesh.cut_selected_object")
        
        row = layout.row()
        row.label(text="Guardar nuevo objeto", icon="COLLECTION_NEW")
        
        row = layout.row()
        row.operator("mesh.save_selected_object")
        
        row = layout.row()
        row.label(text="Colocar objeto guardado", icon="OUTLINER_OB_GROUP_INSTANCE")
        
        row = layout.row()
        row.operator("mesh.place_saved_object")
        
        row = layout.row()
        row.label(text="Exportar objeto", icon="BLENDER")
        
        row = layout.row()
        row.operator("mesh.export_selected_object")


def register():
    bpy.utils.register_class(MESH_OT_move_object_to_world_origin)
    bpy.utils.register_class(MESH_OT_cut_selected_object)
    bpy.utils.register_class(MESH_OT_save_selected_object)
    bpy.utils.register_class(MESH_OT_place_saved_object)
    bpy.utils.register_class(MESH_OT_export_selected_object)
    
    bpy.utils.register_class(VIEW3D_MT_PIE_template)
    
    # Se obtiene el administrador de ventanas actual
    window_manager = bpy.context.window_manager
    
    if window_manager.keyconfigs.addon:
        # Para aplicarlo en la vista 3D
        keymap = window_manager.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')

        # Acceso directo del teclado
        keymap_item = keymap.keymap_items.new('wm.call_menu_pie', 'A', "PRESS", ctrl=True, alt=True)
        keymap_item.properties.name = "VIEW3D_MT_PIE"

        # Se guarda el keymap para que luego se pueda desregistrar
        global_addon_keymaps.append((keymap, keymap_item))
        
    bpy.utils.register_class(ToolsPanel)

def unregister():
    bpy.utils.unregister_class(MESH_OT_move_object_to_world_origin)
    bpy.utils.unregister_class(MESH_OT_cut_selected_object)
    bpy.utils.unregister_class(MESH_OT_save_selected_object)
    bpy.utils.unregister_class(MESH_OT_place_saved_object)
    bpy.utils.unregister_class(MESH_OT_export_selected_object)
    
    bpy.utils.unregister_class(VIEW3D_MT_PIE_template)
   
    # Se obtiene el administrador de ventanas actual
    window_manager = bpy.context.window_manager
    
    # Se verifica si hay keymaps activos
    if window_manager and window_manager.keyconfigs.addon:
        # Se elimina cada keymap guardado
        for keymap, keymap_item in global_addon_keymaps:
            keymap.keymap_items.remove(keymap_item)
            
        # Se limpia la lista de accesos directos
        global_addon_keymaps.clear()
    
    bpy.utils.unregister_class(ToolsPanel)


if __name__ == "__main__":
    register()
