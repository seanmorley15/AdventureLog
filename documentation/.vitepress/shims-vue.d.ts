// Lets plain `tsc` resolve .vue imports. Editors with the Vue extension read
// the components directly and ignore this.
declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<object, object, unknown>;
  export default component;
}
