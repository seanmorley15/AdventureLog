import clsx from "clsx";
import Heading from "@theme/Heading";
import styles from "./styles.module.css";

type FeatureItem = {
  title: string;
  Svg: React.ComponentType<React.ComponentProps<"svg">>;
  description: JSX.Element;
};

const FeatureList: FeatureItem[] = [
  {
    title: "Log Your Travels",
    Svg: require("@site/static/img/undraw_explore.svg").default,
    description: (
      <>
        AdventureLog is a simple way to log your travels and share them with the
        world. You can add photos, notes, and more to your logs.
      </>
    ),
  },
  {
    title: "Track Your World Travel",
    Svg: require("@site/static/img/undraw_adventure.svg").default,
    description: (
      <>
        Keep track of the countries you've visited, the regions you've explored,
        and the places you've been. You can also see your travel stats and
        milestones (coming soon).
      </>
    ),
  },
  {
    title: "View a Map of Your Travels",
    Svg: require("@site/static/img/undraw_map_dark.svg").default,
    description: <>See a map of all the places you've been.</>,
  },
];

function Feature({ title, Svg, description }: FeatureItem) {
  return (
    <div className={clsx("col col--4")}>
      <div className="text--center">
        <Svg className={styles.featureSvg} role="img" />
      </div>
      <div className="text--center padding-horiz--md">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): JSX.Element {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
