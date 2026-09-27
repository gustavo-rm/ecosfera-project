import Navbar from '@/components/landingpage/sections/Navbar'
import Hero from '@/components/landingpage/sections/Hero'
import PlanetSection from '@/components/landingpage/sections/PlanetSection'
import SciencesSection from '@/components/landingpage/sections/SciencesSection'
import TeachersSection from '@/components/landingpage/sections/TeachersSection'
import FinalCta from '@/components/landingpage/sections/FinalCta'
import SiteFooter from '@/components/landingpage/sections/SiteFooter'

export default function Page() {
  return (
    <>
      <Navbar />
      <main>
        <Hero />
        <PlanetSection />
        <SciencesSection />
        <TeachersSection />
        <FinalCta />
      </main>
      <SiteFooter />
    </>
  )
}
